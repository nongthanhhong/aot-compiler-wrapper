/**
 * MyEngine.cpp — Edge Inference Engine Implementation
 * =====================================================
 *
 * Implements the MyEngine class for Android NDK deployment.
 * Uses dlopen to dynamically load vendor NPU libraries and
 * QNN's contextCreateFromBinary API for hardware inference.
 *
 * Part of Domain 3: Edge Runtime (Android NDK / JNI)
 */

#include "MyEngine.h"

#include <android/log.h>
#include <dlfcn.h> // dlopen, dlsym, dlclose
#include <fstream>
#include <sstream>

// TODO: Include a lightweight JSON parser (e.g., nlohmann/json)
// #include "nlohmann/json.hpp"

#define LOG_TAG "MyEngine"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

// --------------------------------------------------------------------------
// Initialization
// --------------------------------------------------------------------------

bool MyEngine::init(const std::string &bundle_path) {
  LOGI("Initializing MyEngine with bundle: %s", bundle_path.c_str());

  // TODO Phase 5: Implement the following steps
  // 1. Unzip deploy_bundle.zip into cache_dir_
  // 2. Parse manifest.json → set input_buffer_size_, output_buffer_size_
  // 3. dlopen the vendor NPU library (e.g., libQnnLpai.so)
  // 4. Load the serialized model via contextCreateFromBinary

  return false; // Not yet implemented
}

// --------------------------------------------------------------------------
// Inference
// --------------------------------------------------------------------------

bool MyEngine::infer(const std::vector<uint8_t> &input_data,
                     std::vector<uint8_t> &output_data) {
  LOGI("Running inference...");

  // TODO Phase 5: Implement inference
  // 1. Validate input_data.size() == input_buffer_size_
  // 2. Copy input_data into the QNN input tensor
  // 3. Execute the graph via QNN API
  // 4. Copy QNN output tensor into output_data

  return false; // Not yet implemented
}

// --------------------------------------------------------------------------
// Cleanup
// --------------------------------------------------------------------------

void MyEngine::cleanup() {
  LOGI("Cleaning up MyEngine resources");

  // TODO Phase 5: Implement cleanup
  // 1. Free QNN context and graph handles
  // 2. dlclose(npu_lib_handle_)

  if (npu_lib_handle_) {
    dlclose(npu_lib_handle_);
    npu_lib_handle_ = nullptr;
  }
  context_ = nullptr;
}

// --------------------------------------------------------------------------
// Private helpers
// --------------------------------------------------------------------------

bool MyEngine::load_manifest(const std::string &manifest_path) {
  LOGI("Loading manifest: %s", manifest_path.c_str());

  // TODO Phase 5: Parse manifest.json
  // - Read input/output tensor shapes and data types
  // - Compute byte sizes for buffer pre-allocation

  return false; // Not yet implemented
}

bool MyEngine::load_npu_library(const std::string &lib_name) {
  LOGI("Loading NPU library: %s", lib_name.c_str());

  npu_lib_handle_ = dlopen(lib_name.c_str(), RTLD_NOW | RTLD_LOCAL);
  if (!npu_lib_handle_) {
    LOGE("dlopen failed: %s", dlerror());
    return false;
  }

  // TODO Phase 5: dlsym to resolve QNN API function pointers
  // - QnnInterface_getProviders
  // - contextCreateFromBinary
  // - graphExecute

  return true;
}

// --------------------------------------------------------------------------
// JNI Bridge (called from Android Java/Kotlin layer)
// --------------------------------------------------------------------------

#include <jni.h>

static MyEngine g_engine;

extern "C" {

JNIEXPORT jboolean JNICALL Java_com_edge_ai_MyEngineJNI_init(
    JNIEnv *env, jobject /* this */, jstring bundle_path) {
  const char *path = env->GetStringUTFChars(bundle_path, nullptr);
  bool ok = g_engine.init(std::string(path));
  env->ReleaseStringUTFChars(bundle_path, path);
  return ok ? JNI_TRUE : JNI_FALSE;
}

JNIEXPORT jbyteArray JNICALL Java_com_edge_ai_MyEngineJNI_infer(
    JNIEnv *env, jobject /* this */, jbyteArray input) {
  // Convert Java byte[] → C++ vector
  jsize len = env->GetArrayLength(input);
  std::vector<uint8_t> input_data(len);
  env->GetByteArrayRegion(input, 0, len,
                          reinterpret_cast<jbyte *>(input_data.data()));

  // Run inference
  std::vector<uint8_t> output_data;
  g_engine.infer(input_data, output_data);

  // Convert C++ vector → Java byte[]
  jbyteArray result = env->NewByteArray(output_data.size());
  env->SetByteArrayRegion(result, 0, output_data.size(),
                          reinterpret_cast<const jbyte *>(output_data.data()));
  return result;
}

JNIEXPORT void JNICALL
Java_com_edge_ai_MyEngineJNI_cleanup(JNIEnv * /* env */, jobject /* this */) {
  g_engine.cleanup();
}

} // extern "C"
