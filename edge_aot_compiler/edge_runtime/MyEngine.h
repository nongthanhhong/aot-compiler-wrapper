/**
 * MyEngine.h — Minimal C++ Edge Inference API
 * =============================================
 *
 * Declares the MyEngine class that:
 *   1. Unpacks the deploy_bundle.zip on the Android device
 *   2. Parses manifest.json for buffer sizing
 *   3. Loads the vendor NPU library via dlopen
 *   4. Runs inference through the NPU binary
 *
 * Part of Domain 3: Edge Runtime (Android NDK / JNI)
 */

#ifndef MY_ENGINE_H
#define MY_ENGINE_H

#include <cstdint>
#include <string>
#include <vector>

class MyEngine {
public:
    /**
     * Initialize the engine from a deployment bundle.
     *
     * @param bundle_path  Path to deploy_bundle.zip in the app's cache dir.
     * @return true if initialization succeeded.
     */
    bool init(const std::string& bundle_path);

    /**
     * Run inference on the given input buffer.
     *
     * @param input_data  Raw input bytes (size must match manifest input spec).
     * @param output_data Preallocated output buffer.
     * @return true if inference succeeded.
     */
    bool infer(const std::vector<uint8_t>& input_data,
               std::vector<uint8_t>& output_data);

    /**
     * Release all NPU resources, unload the vendor library.
     */
    void cleanup();

private:
    void*       npu_lib_handle_ = nullptr;  // dlopen handle
    void*       context_        = nullptr;  // QNN context from binary
    std::string cache_dir_;                 // Extracted bundle location

    // Buffer sizes read from manifest.json
    size_t input_buffer_size_  = 0;
    size_t output_buffer_size_ = 0;

    bool load_manifest(const std::string& manifest_path);
    bool load_npu_library(const std::string& lib_name);
};

#endif // MY_ENGINE_H
