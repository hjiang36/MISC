#include <iostream>
#include <vector>

#include <cuda.h>
#include "nvEncodeAPI.h"

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"


uint8_t mvEncodeU8(int16_t x) {
    int16_t val = x / 4 + 127;
    if (val < 0) {
        return 0;
    } else if (val > 255) {
        return 255;
    } else {
        return (uint8_t)val;
    }
} 


int main(int argc, char *argv[]) {
    if (argc < 4) {
        std::cout << "Usage: mv_nvenc ref_file in_file output_file" << std::endl;
        return -1;
    }

    // Load reference frame and input frame.
    int wRef, hRef, cRef, wIn, hIn, cIn;
    uint8_t *refImageData = stbi_load(argv[1], &wRef, &hRef, &cRef, 4);
    uint8_t *inputImageData = stbi_load(argv[2], &wIn, &hIn, &cIn, 4);
    assert(wRef == wIn && hRef == hIn && cRef == cIn);
    if (refImageData != nullptr) {
        std::cout << "Loaded image with resolution: " << wRef << "x" << hRef << "x" << cRef << std::endl;
    } else {
        std::cerr << "Load image failed";
        return -1;
    }

    stbi_write_png("ref_image.png", wRef, hRef, 4, refImageData, wRef * 4);
    stbi_write_png("input_image.png", wRef, hRef, 4, inputImageData, wRef * 4);

    // Create CUDA context
    cuInit(0);
    int nGpu = 0;
    cuDeviceGetCount(&nGpu);
    
    CUdevice cuDevice = 0;
    cuDeviceGet(&cuDevice, 0);
    
    char szDeviceName[80];
    cuDeviceGetName(szDeviceName, sizeof(szDeviceName), cuDevice);
    std::cout << "GPU in use: " << szDeviceName << std::endl;
    
    CUcontext cuContext = NULL;
    cuCtxCreate(&cuContext, 0, cuDevice);

    // Load NVENC API
    uint32_t version = 0;
    uint32_t currentVersion = (NVENCAPI_MAJOR_VERSION << 4) | NVENCAPI_MINOR_VERSION;
    NvEncodeAPIGetMaxSupportedVersion(&version);
    if (currentVersion > version)
    {
        std::cerr << "Current Driver Version does not support this NvEncodeAPI version" << std::endl;
        return -1;
    }


    NV_ENCODE_API_FUNCTION_LIST nvenc = { NV_ENCODE_API_FUNCTION_LIST_VER };
    NvEncodeAPICreateInstance(&nvenc);

    if (!nvenc.nvEncOpenEncodeSession) {
        std::cerr << "EncodeAPI not found" << std::endl;
        return -1;
    }

    NV_ENC_OPEN_ENCODE_SESSION_EX_PARAMS encodeSessionExParams = { NV_ENC_OPEN_ENCODE_SESSION_EX_PARAMS_VER };
    encodeSessionExParams.device = cuContext;
    encodeSessionExParams.deviceType = NV_ENC_DEVICE_TYPE_CUDA;
    encodeSessionExParams.apiVersion = NVENCAPI_VERSION;
    void *hEncoder = nullptr;
    if (nvenc.nvEncOpenEncodeSessionEx(&encodeSessionExParams, &hEncoder) != NV_ENC_SUCCESS) {
        std::cerr << "Failed to open encoder session." << std::endl;
        return -1;
    }

    // Initialize encoder session.
    NV_ENC_BUFFER_FORMAT eFormat = NV_ENC_BUFFER_FORMAT_ARGB;
    NV_ENC_INITIALIZE_PARAMS initializeParams = { NV_ENC_INITIALIZE_PARAMS_VER };
    NV_ENC_CONFIG encodeConfig = { NV_ENC_CONFIG_VER };
    initializeParams.encodeConfig = &encodeConfig;

    memset(initializeParams.encodeConfig, 0, sizeof(NV_ENC_CONFIG));
    auto pEncodeConfig = initializeParams.encodeConfig;
    memset(&initializeParams, 0, sizeof(NV_ENC_INITIALIZE_PARAMS));
    initializeParams.encodeConfig = pEncodeConfig;


    initializeParams.encodeConfig->version = NV_ENC_CONFIG_VER;
    initializeParams.version = NV_ENC_INITIALIZE_PARAMS_VER;

    initializeParams.encodeGUID = NV_ENC_CODEC_H264_GUID;
    initializeParams.presetGUID = NV_ENC_PRESET_P5_GUID;
    initializeParams.encodeWidth = wRef;
    initializeParams.encodeHeight = hRef;
    initializeParams.darWidth = wRef;
    initializeParams.darHeight = hRef;
    initializeParams.frameRateNum = 30;
    initializeParams.frameRateDen = 1;
    initializeParams.enablePTD = 1;
    initializeParams.reportSliceOffsets = 0;
    initializeParams.enableSubFrameWrite = 0;
    initializeParams.maxEncodeWidth = wRef;
    initializeParams.maxEncodeHeight = hRef;
    initializeParams.enableMEOnlyMode = true;
    initializeParams.enableOutputInVidmem = false;

    NV_ENC_PRESET_CONFIG presetConfig = { NV_ENC_PRESET_CONFIG_VER, { NV_ENC_CONFIG_VER } };
    nvenc.nvEncGetEncodePresetConfig(hEncoder, NV_ENC_CODEC_H264_GUID, NV_ENC_PRESET_P5_GUID, &presetConfig);
    memcpy(initializeParams.encodeConfig, &presetConfig.presetCfg, sizeof(NV_ENC_CONFIG));
    initializeParams.encodeConfig->frameIntervalP = 1;
    initializeParams.encodeConfig->gopLength = NVENC_INFINITE_GOPLENGTH;
    initializeParams.encodeConfig->rcParams.rateControlMode = NV_ENC_PARAMS_RC_CONSTQP;
    initializeParams.encodeConfig->rcParams.constQP = { 28, 31, 25 };
    initializeParams.encodeConfig->encodeCodecConfig.h264Config.idrPeriod = initializeParams.encodeConfig->gopLength;


    if (nvenc.nvEncInitializeEncoder(hEncoder, &initializeParams) != NV_ENC_SUCCESS) {
        std::cerr << "Initialize encoder failed" << std::endl;
        return -1;
    }
    
    // Allocate CUDA buffers for reference and input frames.
    NV_ENC_REGISTERED_PTR registeredRefPtr = nullptr;
    NV_ENC_REGISTERED_PTR registeredInPtr = nullptr;
    for (int i = 0; i < 2; i++) {
       cuCtxPushCurrent(cuContext);
        
        CUdeviceptr pBuffer;
        size_t cudaPitch = 0;
        if (cuMemAllocPitch(&pBuffer, &cudaPitch, wRef * 4, hRef, 16) != CUDA_SUCCESS) {
            std::cerr << "Failed to allocate cuda buffer" << std::endl;
            return -1;
        }
        
        cuCtxPopCurrent(nullptr);
        
        NV_ENC_REGISTER_RESOURCE registerResource = { NV_ENC_REGISTER_RESOURCE_VER };
        registerResource.resourceType = NV_ENC_INPUT_RESOURCE_TYPE_CUDADEVICEPTR;
        registerResource.resourceToRegister = (void*) pBuffer;
        registerResource.width = wRef;
        registerResource.height = hRef;
        registerResource.pitch = (uint32_t) cudaPitch;
        registerResource.bufferFormat = eFormat;
        registerResource.bufferUsage = NV_ENC_INPUT_IMAGE;
        registerResource.pInputFencePoint = nullptr;
        registerResource.pOutputFencePoint = nullptr;
        if (nvenc.nvEncRegisterResource(hEncoder, &registerResource) != NV_ENC_SUCCESS) {
            std::cerr << "NVENC register resources failed";
            return -1;
        }

        if (i == 0) {
            registeredRefPtr = registerResource.registeredResource;
        } else {
            registeredInPtr = registerResource.registeredResource;
        }

        // Copy image to CUDA device memory.
        cuCtxPushCurrent(cuContext);
        CUDA_MEMCPY2D m = { 0 };
        m.srcMemoryType = CU_MEMORYTYPE_HOST;
        m.srcHost = (i == 0) ? refImageData : inputImageData;
        m.srcPitch = wRef * 4;
        m.dstMemoryType = CU_MEMORYTYPE_DEVICE;
        m.dstDevice = pBuffer;
        m.dstPitch = cudaPitch;
        m.WidthInBytes = wRef * 4;
        m.Height = hRef;
        if (cuMemcpy2D(&m) != CUDA_SUCCESS) {
            std::cerr << "Failed to copy frames to CUDA memory" << std::endl;
            return -1;
        }
    }

    // Allocate motion vector output buffer.
    NV_ENC_CREATE_MV_BUFFER createMVBuffer = { NV_ENC_CREATE_MV_BUFFER_VER };
    if (nvenc.nvEncCreateMVBuffer(hEncoder, &createMVBuffer) != NV_ENC_SUCCESS) {
        std::cerr << "Failed to create motion vector output buffer" << std::endl;
        return -1;
    }
    NV_ENC_OUTPUT_PTR mvBufferPtr = createMVBuffer.mvBuffer;

    // Map resources
    NV_ENC_MAP_INPUT_RESOURCE mapInputResource = { NV_ENC_MAP_INPUT_RESOURCE_VER };
    mapInputResource.registeredResource = registeredInPtr;
    if (nvenc.nvEncMapInputResource(hEncoder, &mapInputResource) != NV_ENC_SUCCESS) {
        std::cerr << "Failed to map registered resources for input frame" << std::endl;
        return -1;
    }
    NV_ENC_INPUT_PTR nvencInPtr = mapInputResource.mappedResource;
    
    mapInputResource.registeredResource = registeredRefPtr;
    if (nvenc.nvEncMapInputResource(hEncoder, &mapInputResource) != NV_ENC_SUCCESS) {
        std::cerr << "Failed to map registered resources for reference frame" << std::endl;
        return -1;
    }
    NV_ENC_INPUT_PTR nvencRefPtr = mapInputResource.mappedResource;

    // Do motion estimation.
    NV_ENC_MEONLY_PARAMS meParams = { NV_ENC_MEONLY_PARAMS_VER };
    meParams.inputBuffer = nvencInPtr;
    meParams.referenceFrame = nvencRefPtr;
    meParams.inputWidth = wRef;
    meParams.inputHeight = hRef;
    meParams.mvBuffer = mvBufferPtr;
    meParams.completionEvent = nullptr;
    if (nvenc.nvEncRunMotionEstimationOnly(hEncoder, &meParams) != NV_ENC_SUCCESS) {
        std::cerr << "Run motion estimation only mode failed" << std::endl;
        return -1;
    }
    
    // Read back motion vector from packets.
    std::vector<uint8_t> mvData;
    
    NV_ENC_LOCK_BITSTREAM lockBitstreamData = { NV_ENC_LOCK_BITSTREAM_VER };
    lockBitstreamData.outputBitstream = mvBufferPtr;
    lockBitstreamData.doNotWait = false;
    if (nvenc.nvEncLockBitstream(hEncoder, &lockBitstreamData) != NV_ENC_SUCCESS) {
        std::cerr << "Lock bitstream failed" << std::endl;
    }
  
    uint8_t *pData = (uint8_t *)lockBitstreamData.bitstreamBufferPtr;
    mvData.clear();
    mvData.insert(mvData.end(), &pData[0], &pData[lockBitstreamData.bitstreamSizeInBytes]);

    if (nvenc.nvEncUnlockBitstream(hEncoder, lockBitstreamData.outputBitstream) != NV_ENC_SUCCESS) {
        std::cerr << "Unloack bitstream failed" << std::endl;
        return -1;
    }

    // Parse motion vectors and write to file.
    uint32_t mvWidth = (wRef + 15) / 16;
    uint32_t mvHeight = (hRef + 15) / 16;
    std::vector<uint8_t> mvImage(mvWidth * 2 * mvHeight * 2 * 3);
    memset(mvImage.data(), 127, mvImage.size());
    uint32_t mvStride = mvWidth * 2 * 3;
    NV_ENC_H264_MV_DATA *outputMV = (NV_ENC_H264_MV_DATA *)mvData.data();
    uint32_t mvIndex = 0;
    for (uint32_t i = 0; i < mvHeight; i++) {
        for (uint32_t j = 0; j < mvWidth; j++) {
            mvImage[2 * i * mvStride + 2 * j * 3] = mvEncodeU8(outputMV[mvIndex].mv[0].mvx);
            mvImage[2 * i * mvStride + 2 * j * 3 + 1] = mvEncodeU8(outputMV[mvIndex].mv[0].mvy);

            mvImage[2 * i * mvStride + (2 * j + 1) * 3] = mvEncodeU8(outputMV[mvIndex].mv[1].mvx);
            mvImage[2 * i * mvStride + (2 * j + 1) * 3 + 1] = mvEncodeU8(outputMV[mvIndex].mv[1].mvy);

            mvImage[(2 * i + 1) * mvStride + 2 * j * 3] = mvEncodeU8(outputMV[mvIndex].mv[2].mvx);
            mvImage[(2 * i + 1) * mvStride + 2 * j * 3 + 1] = mvEncodeU8(outputMV[mvIndex].mv[2].mvy);

            mvImage[(2 * i + 1) * mvStride + (2 * j + 1) * 3] = mvEncodeU8(outputMV[mvIndex].mv[3].mvx);
            mvImage[(2 * i + 1) * mvStride + (2 * j + 1) * 3 + 1] = mvEncodeU8(outputMV[mvIndex].mv[3].mvy);

            mvIndex++;
        }
    }
    
    if (stbi_write_png(argv[3], mvWidth * 2, mvHeight * 2, 3, mvImage.data(), mvStride) == 0) {
        std::cerr << "Failed to write output motion vector to file" << std::endl;
        return -1;
    } else {
        std::cout << "Motion vector write to file: " << argv[3];
    }

    // Clean up
    // Unmapp resources.
    if (nvenc.nvEncUnmapInputResource(hEncoder, nvencInPtr) != NV_ENC_SUCCESS) {
        std::cerr << "Failed to unmap resources for input image." << std::endl;
        return -1;
    }
    if (nvenc.nvEncUnmapInputResource(hEncoder, nvencRefPtr) != NV_ENC_SUCCESS) {
        std::cerr << "Failed to unmap resources for reference image." << std::endl;
        return -1;
    }

    // Release motion vector buffer.
    if (nvenc.nvEncDestroyMVBuffer(hEncoder, mvBufferPtr) != NV_ENC_SUCCESS) {
        std::cerr << "Failed to destroy motion vector buffer";
        return -1;
    }
    
    // Destory encoder.
    nvenc.nvEncDestroyEncoder(hEncoder);
    
    // Destroy cuda context
    cuCtxDestroy(cuContext);

    // Release input images.
    stbi_image_free(refImageData);
    stbi_image_free(inputImageData);
    return 0;
}
