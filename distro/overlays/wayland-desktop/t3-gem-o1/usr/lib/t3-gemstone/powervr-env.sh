#!/bin/sh

T3_GPU_PREFIX=/opt/ti-gpu
T3_GPU_LIB="$T3_GPU_PREFIX/lib"

export T3_GPU_PREFIX
export LD_LIBRARY_PATH="$T3_GPU_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LIBGL_DRIVERS_PATH="$T3_GPU_LIB/dri"
export GBM_BACKENDS_PATH="$T3_GPU_LIB/gbm"
export MESA_LOADER_DRIVER_OVERRIDE=pvr

if [ -f "$T3_GPU_PREFIX/share/glvnd/egl_vendor.d/50_mesa.json" ]; then
    export __EGL_VENDOR_LIBRARY_FILENAMES="$T3_GPU_PREFIX/share/glvnd/egl_vendor.d/50_mesa.json"
fi
