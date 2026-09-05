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
      <a href="https://www.instagram.com/nidhi.pxl/" target="_blank" rel="noopener noreferrer" class="instagram-link" title="Instagram @nidhi.pxl">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
          <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
          <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
        </svg>
        <span>@nidhi.pxl</span>
      </a>
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

    const container = document.getElementById("{album}-gallery");

    fetch("images.json")
      .then(res => res.json())
      .then(data => {{
        if (data.{album}) {{
          data.{album}.forEach(({{ file, caption, alt }}) => {{
            const fullSrc  = `images/{album}/${{file}}`;
            const thumbSrc = `images/{album}/thumbs/${{file}}`;

            const link = document.createElement("a");
            link.href = fullSrc;
            link.setAttribute("data-sub-html", caption ? `<div class="lg-caption-wrap">${{caption}}</div>` : "");

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

            lgEl.addEventListener('lgAfterOpen', autoFullscreenOnMobileLandscape);
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
