import os

albums = ["animals", "astro", "flowers", "insects", "landscapes", "skies"]

def generate_album_html(album):
    title = album.capitalize()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title} Album - Nidhi Mekaraj Photography</title>

  <!-- Custom CSS -->
  <link rel="stylesheet" href="css/style.css" />
  
  <!-- LightGallery CSS -->
  <link href="https://cdn.jsdelivr.net/npm/lightgallery@2.7.2/css/lightgallery-bundle.min.css" rel="stylesheet" />

  <!-- JustifiedGallery CSS -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/justifiedGallery@3.8.1/dist/css/justifiedGallery.min.css" />

  <!-- jQuery -->
  <script src="https://cdn.jsdelivr.net/npm/jquery@3.6.4/dist/jquery.min.js"></script>

  <!-- JustifiedGallery JS -->
  <script src="https://cdn.jsdelivr.net/npm/justifiedGallery@3.8.1/dist/js/jquery.justifiedGallery.min.js"></script>

  <script>
    // Clean URL: Automatically remove .html extension from browser address bar
    if (window.location.pathname.endsWith('.html')) {{
      const cleanPath = window.location.pathname.replace(/\\/{album}\\.html$/, '/{album}').replace(/\\.html$/, '');
      window.history.replaceState(null, '', cleanPath + window.location.search + window.location.hash);
    }}
  </script>
</head>

<body>
  <header id="site-header">
    <h1>{title}</h1>
    <div class="header-nav">
      <a href="./" class="back-link">← Back to Portfolio</a>
    </div>
  </header>

  <main>
    <div class="gallery-section">
      <div id="{album}-gallery" class="justified-gallery"></div>
      <div class="gallery-end">✦ End of {title} Album ✦</div>
    </div>
  </main>

  <!-- Scroll To Top Button -->
  <button id="scrollToTop" title="Back to Top" onclick="scrollToTop()">↑</button>

  <!-- LightGallery JS & Plugins -->
  <script src="https://cdn.jsdelivr.net/npm/lightgallery@2.7.2/lightgallery.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/lightgallery@2.7.2/plugins/zoom/lg-zoom.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/lightgallery@2.7.2/plugins/thumbnail/lg-thumbnail.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/lightgallery@2.7.2/plugins/fullscreen/lg-fullscreen.min.js"></script>

  <script>
    // Prevent Right-Click & Image Dragging to protect images
    document.addEventListener('contextmenu', (e) => e.preventDefault());
    document.addEventListener('dragstart', (e) => e.preventDefault());

    // Pressing 'F' or 'f' key toggles Fullscreen mode when LightGallery is open
    document.addEventListener('keydown', (e) => {{
      if ((e.key === 'f' || e.key === 'F') && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {{
        const lgContainer = document.querySelector('.lg-container.lg-show');
        if (lgContainer) {{
          const fsBtn = lgContainer.querySelector('.lg-fullscreen');
          if (fsBtn) {{
            fsBtn.click();
          }}
        }}
      }}
    }});

    // Auto-enter fullscreen mode on mobile landscape orientation
    function autoFullscreenOnMobileLandscape() {{
      const isMobileLandscape = window.matchMedia("(orientation: landscape) and (max-height: 650px)").matches;
      const lgContainer = document.querySelector('.lg-container.lg-show');
      if (isMobileLandscape && lgContainer && !lgContainer.classList.contains('lg-fullscreen-on')) {{
        const fsBtn = lgContainer.querySelector('.lg-fullscreen');
        if (fsBtn) {{
          fsBtn.click();
        }}
      }}
    }}

    window.addEventListener('resize', autoFullscreenOnMobileLandscape);
    window.addEventListener('orientationchange', autoFullscreenOnMobileLandscape);

    function setupInfoButton(lgEl) {{
      lgEl.addEventListener('lgAfterOpen', () => {{
        const toolbar = document.querySelector('.lg-container .lg-toolbar');
        if (toolbar && !toolbar.querySelector('.lg-info-wrap')) {{
          const infoWrap = document.createElement('div');
          infoWrap.className = 'lg-info-wrap';
          infoWrap.innerHTML = `
            <button class="lg-info-btn" aria-label="Image Information" title="Image Metadata">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
            </button>
            <div class="lg-info-popover" id="lg-info-popover">
              <div class="lg-info-header">Image Specs</div>
              <div class="lg-info-content">
                <div class="lg-info-row"><span class="lg-info-label">F-stop:</span><span class="lg-info-val" id="info-fstop">N/A</span></div>
                <div class="lg-info-row"><span class="lg-info-label">Shutter Speed:</span><span class="lg-info-val" id="info-shutter">N/A</span></div>
                <div class="lg-info-row"><span class="lg-info-label">ISO:</span><span class="lg-info-val" id="info-iso">N/A</span></div>
                <div class="lg-info-row"><span class="lg-info-label">Focal Length:</span><span class="lg-info-val" id="info-focal">N/A</span></div>
              </div>
            </div>
          `;

          const closeBtn = toolbar.querySelector('.lg-close');
          if (closeBtn) {{
            toolbar.insertBefore(infoWrap, closeBtn);
          }} else {{
            toolbar.appendChild(infoWrap);
          }}

          const infoBtn = infoWrap.querySelector('.lg-info-btn');
          infoBtn.addEventListener('click', (e) => {{
            e.stopPropagation();
            infoWrap.classList.toggle('active');
          }});

          document.addEventListener('click', (e) => {{
            if (!infoWrap.contains(e.target)) {{
              infoWrap.classList.remove('active');
            }}
          }});
        }}
        autoFullscreenOnMobileLandscape();
      }});

      lgEl.addEventListener('lgAfterSlide', (e) => {{
        const items = lgEl.querySelectorAll('a[data-sub-html]');
        const activeItem = items[e.detail.index];
        if (!activeItem) return;

        const fstopEl = document.getElementById('info-fstop');
        const shutterEl = document.getElementById('info-shutter');
        const isoEl = document.getElementById('info-iso');
        const focalEl = document.getElementById('info-focal');

        if (fstopEl) fstopEl.textContent = activeItem.dataset.fstop || 'N/A';
        if (shutterEl) shutterEl.textContent = activeItem.dataset.shutter || 'N/A';
        if (isoEl) isoEl.textContent = activeItem.dataset.iso || 'N/A';
        if (focalEl) focalEl.textContent = activeItem.dataset.focal || 'N/A';
      }});
    }}

    const container = document.getElementById("{album}-gallery");

    fetch("images.json")
      .then(res => res.json())
      .then(data => {{
        if (data.{album}) {{
          data.{album}.forEach(({{ file, caption, alt, exif }}) => {{
            const fullSrc  = `images/{album}/${{file}}`;
            const thumbSrc = `images/{album}/thumbs/${{file}}`;

            const link = document.createElement("a");
            link.href = fullSrc;
            link.setAttribute("data-sub-html", caption ? `<div class="lg-caption-wrap">${{caption}}</div>` : "");

            if (exif) {{
              link.dataset.fstop = exif.fstop || 'N/A';
              link.dataset.shutter = exif.shutter || 'N/A';
              link.dataset.iso = exif.iso || 'N/A';
              link.dataset.focal = exif.focal || 'N/A';
            }} else {{
              link.dataset.fstop = 'N/A';
              link.dataset.shutter = 'N/A';
              link.dataset.iso = 'N/A';
              link.dataset.focal = 'N/A';
            }}

            const img = document.createElement("img");
            img.src = thumbSrc;
            img.alt = alt || "";
            img.loading = "lazy";
            img.onerror = () => {{
              img.src = fullSrc;
            }};

            link.appendChild(img);
            container.appendChild(link);
          }});
        }}

        $(function () {{
          const rowHeight = window.innerWidth > 1600 ? 160 : 200;
          $('#{album}-gallery').justifiedGallery({{
            rowHeight: rowHeight,
            margins: 6,
            lastRow: 'nojustify'
          }}).on('jg.complete', function () {{
            const lgEl = document.getElementById('{album}-gallery');
            lightGallery(lgEl, {{
              plugins: [lgZoom, lgThumbnail, lgFullscreen],
              fullScreen: true,
              speed: 500,
              download: false,
              share: false,
              doubleTapZoom: 1.5
            }});

            setupInfoButton(lgEl);
          }});
        }});
      }});

    // Scroll to Top
    window.addEventListener('scroll', () => {{
      document.getElementById('scrollToTop').classList.toggle('show', window.scrollY > 300);
    }});

    function scrollToTop() {{
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    // Header opacity fade out on scroll
    (function () {{
      const header = document.getElementById('site-header');

      function syncHeaderOffset() {{
        document.documentElement.style.setProperty(
          '--header-height', header.offsetHeight + 'px'
        );
      }}
      syncHeaderOffset();
      window.addEventListener('resize', syncHeaderOffset, {{ passive: true }});

      window.addEventListener('scroll', () => {{
        const fadeDistance = header.offsetHeight;
        const opacity = Math.max(0, 1 - window.scrollY / fadeDistance);
        header.style.opacity = opacity;
        header.style.pointerEvents = opacity === 0 ? 'none' : '';
      }}, {{ passive: true }});
    }})();
  </script>
</body>
</html>
"""

def main():
    for album in albums:
        filepath = f"{album}.html"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(generate_album_html(album))
        print(f"  + Updated {filepath}")

if __name__ == "__main__":
    main()
