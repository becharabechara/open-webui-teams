# Docling Docker Build Optimization Strategy

## Problem Analysis
The Docling Docker build fails with "no space left on device" because:
1. **Large Base Image**: `quay.io/docling-project/docling-serve:latest` is ~5.4GB with heavy ML dependencies
2. **Limited Disk Space**: Azure DevOps hosted agents have ~29GB total, only ~1-2GB free after base image extraction
3. **Docker Layer Overhead**: Each RUN command creates intermediate layers that consume additional space

## Implemented Solutions

### 1. Optimized Dockerfile (`Dockerfile-docling`)
- **Single RUN Layer**: Combined all downloads and cleanup into one layer
- **Efficient Downloads**: Try archive download first, fallback to individual files
- **Immediate Cleanup**: Remove temporary files in the same layer
- **Silent Failures**: Use `2>/dev/null || true` for non-critical operations

### 2. Pipeline Improvements
- **Aggressive Cleanup**: Enhanced cleanup script with system-level temp file removal
- **BuildKit Optimizations**: Enabled Docker BuildKit for better caching and space management
- **Disk Space Monitoring**: Real-time monitoring during build with warnings
- **Registry Caching**: Use ACR as cache backend to avoid rebuilding unchanged layers
- **Immediate Post-Build Cleanup**: Remove built images immediately after push

### 3. Multi-Stage Alternative (`Dockerfile-docling-multistage`)
If space issues persist, use the multi-stage build:
- **Separate Download Stage**: Uses minimal Alpine image for downloads (~5MB base)
- **Clean Final Stage**: Only copies essential files to final image
- **Reduced Intermediate Layers**: Minimizes space usage during build

## Usage Instructions

### Standard Build (Recommended)
Uses the optimized `Dockerfile-docling` with current pipeline improvements.

### Multi-Stage Build (Fallback)
If space issues continue, update the pipeline to use `Dockerfile-docling-multistage`:

```yaml
# In azure-pipelines-docex-codeex.yml, change:
-f $(doclingDockerfilePath) .
# To:
-f Dockerfile-docling-multistage .
```

## Alternative Strategies (If Issues Persist)

### 1. Self-Hosted Agent
Deploy a self-hosted Azure DevOps agent with:
- **Larger Disk**: At least 100GB available space
- **More Memory**: 16GB+ RAM for large ML model builds
- **SSD Storage**: Faster I/O for large file operations

### 2. External Image Building
- **Azure Container Registry Tasks**: Use ACR Build for large images
- **GitHub Actions**: Build in GitHub with larger runners
- **Scheduled Builds**: Build images separately from deployment pipeline

### 3. Base Image Optimization
- Create a custom lighter base image with only necessary ML dependencies
- Pre-build Tesseract language files into a separate layer
- Use distroless or minimal base images where possible

### 4. Build Caching Strategy
- **Layer Caching**: Leverage Docker layer caching effectively
- **Dependency Caching**: Cache downloaded files in separate stages
- **Registry Mirroring**: Use closer registry mirrors for faster downloads

## Monitoring and Troubleshooting

### Disk Space Monitoring
The pipeline now includes real-time disk space monitoring:
- Pre-build space check (requires 20GB minimum)
- During-build monitoring (warns at <5GB remaining)
- Post-build cleanup verification

### Debug Information
Enhanced logging provides:
- Available disk space at each stage
- Docker system usage (`docker system df`)
- Build progress with layer-by-layer space consumption
- Failed layer identification for quick debugging

### Emergency Fallback
If build fails due to space:
1. The pipeline will show exact disk usage at failure point
2. Consider using the multi-stage Dockerfile
3. Temporary solution: Manually push a pre-built image to ACR
4. Long-term: Implement self-hosted agent or external build service

## Performance Expectations

### Build Times
- **Initial Build**: 15-25 minutes (downloading 5.4GB base image)
- **Cached Build**: 5-10 minutes (with registry caching)
- **Multi-Stage Build**: 10-20 minutes (additional stage overhead)

### Space Usage
- **Standard Build**: Peak ~15-20GB during build
- **Multi-Stage Build**: Peak ~10-15GB during build
- **Final Image Size**: ~5.5GB (base + language files ~100MB)

## Recommendations Priority

1. **✅ Implemented**: Use optimized Dockerfile with BuildKit and enhanced cleanup
2. **🔄 If Issues Persist**: Switch to multi-stage Dockerfile
3. **📋 Long-term**: Implement self-hosted agent with larger disk capacity
4. **🏗️ Advanced**: Create custom lighter base image or external build process