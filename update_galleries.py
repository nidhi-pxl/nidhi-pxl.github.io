import os

albums = ["flowers", "skies"]
image_base = "images"

for album in albums:
    folder = os.path.join(image_base, album)
    if not os.path.exists(folder):
        continue

    images = sorted([img for img in os.listdir(folder) if img.endswith((".jpg", ".png", ".jpeg"))])
    image_tags = "\n".join([f'      <img src="{image_base}/{album}/{img}" alt="{img}">' for img in images])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{album.title()} Album</title>
  <link rel="stylesheet" href="css/style.css" />
</head>
<body>
  <header>
    <h1>{album.title()}</h1>
    <a href="index.html">← Back to Home</a>
  </header>
  <main>
    <div class="gallery">
{image_tags}
    </div>
  </main>
</body>
</html>"""

    with open(f"{album}.html", "w") as f:
        f.write(html)

print("Gallery pages updated.")
