<template>
  <section v-if="variant === 'detail'" class="detail-loader" role="status" aria-live="polite">
    <span class="sr-only">게임 정보를 불러오는 중입니다.</span>
    <div class="detail-loader-hero">
      <div class="detail-loader-media skeleton-shimmer">
        <span class="loader-ring" aria-hidden="true"></span>
      </div>
      <div class="detail-loader-info">
        <span class="skeleton-line eyebrow"></span>
        <span class="skeleton-line title"></span>
        <span class="skeleton-line subtitle"></span>
        <div class="detail-loader-tags">
          <span class="skeleton-pill"></span>
          <span class="skeleton-pill short"></span>
          <span class="skeleton-pill"></span>
        </div>
        <span class="skeleton-line price"></span>
      </div>
    </div>

    <div class="detail-loader-grid">
      <div class="detail-loader-panel">
        <span class="skeleton-line panel-title"></span>
        <span class="skeleton-line panel-text"></span>
        <span class="skeleton-line panel-text narrow"></span>
      </div>
      <div class="detail-loader-panel compact">
        <span class="skeleton-line panel-title"></span>
        <span class="skeleton-line panel-text"></span>
      </div>
    </div>
  </section>

  <section v-else class="page-loader" role="status" aria-live="polite">
    <span class="loader-ring" aria-hidden="true"></span>
    <span class="sr-only">콘텐츠를 불러오는 중입니다.</span>
  </section>
</template>

<script setup>
defineProps({
  variant: { type: String, default: 'default' },
})
</script>

<style scoped>
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

.page-loader {
  display: grid;
  place-items: center;
  min-height: 260px;
  padding: 40px;
}

.detail-loader {
  display: grid;
  gap: 28px;
  width: min(1180px, 100%);
  margin: 0 auto;
  padding: 30px 0 56px;
}

.detail-loader-hero {
  display: grid;
  grid-template-columns: minmax(280px, 0.95fr) minmax(280px, 0.65fr);
  gap: 40px;
  align-items: center;
  min-height: 320px;
  border-bottom: 1px solid rgba(217, 217, 216, 0.14);
  padding-bottom: 28px;
}

.detail-loader-media {
  position: relative;
  display: grid;
  place-items: center;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: #252525;
}

.detail-loader-info,
.detail-loader-panel {
  display: grid;
  gap: 14px;
}

.detail-loader-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 2px;
}

.detail-loader-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(260px, 0.85fr);
  gap: 28px;
}

.detail-loader-panel {
  min-height: 150px;
  border-bottom: 1px solid rgba(217, 217, 216, 0.14);
  padding: 20px 0 24px;
}

.detail-loader-panel.compact {
  min-height: 118px;
}

.loader-ring {
  width: 42px;
  height: 42px;
  border: 3px solid rgba(217, 217, 216, 0.2);
  border-top-color: #3183d8;
  border-radius: 50%;
  animation: loader-spin 1.1s linear infinite;
}

.skeleton-line,
.skeleton-pill {
  display: block;
  overflow: hidden;
  border-radius: 999px;
  background: #252525;
  color: transparent;
}

.skeleton-line {
  height: 13px;
}

.skeleton-line.eyebrow {
  width: 34%;
  height: 10px;
}

.skeleton-line.title {
  width: 76%;
  height: 52px;
  border-radius: 4px;
}

.skeleton-line.subtitle {
  width: 52%;
  height: 16px;
}

.skeleton-line.price {
  width: 30%;
  height: 30px;
  margin-top: 12px;
  border-radius: 4px;
}

.skeleton-line.panel-title {
  width: 36%;
  height: 22px;
  border-radius: 4px;
}

.skeleton-line.panel-text {
  width: 88%;
  height: 14px;
}

.skeleton-line.panel-text.narrow {
  width: 62%;
}

.skeleton-pill {
  width: 78px;
  height: 25px;
}

.skeleton-pill.short {
  width: 56px;
}

.skeleton-shimmer,
.skeleton-line,
.skeleton-pill {
  position: relative;
}

.skeleton-shimmer::after,
.skeleton-line::after,
.skeleton-pill::after {
  position: absolute;
  inset: 0;
  content: "";
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.08), transparent);
  animation: loader-shimmer 1.45s ease-in-out infinite;
  transform: translateX(-100%);
}

@keyframes loader-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes loader-shimmer {
  100% {
    transform: translateX(100%);
  }
}

@media (max-width: 900px) {
  .detail-loader-hero,
  .detail-loader-grid {
    grid-template-columns: 1fr;
    gap: 24px;
  }

  .detail-loader-hero {
    min-height: 0;
  }
}

@media (max-width: 640px) {
  .detail-loader {
    padding-top: 18px;
  }

  .skeleton-line.title {
    height: 38px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .loader-ring,
  .skeleton-shimmer::after,
  .skeleton-line::after,
  .skeleton-pill::after {
    animation: none;
  }
}
</style>
