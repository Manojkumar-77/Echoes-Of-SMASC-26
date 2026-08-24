# Echoes Of SMASC '26

> **Tagline:** Three Years. Countless Memories. One Story.  
> **Dedicated to:** BCA Class of 2026  
> **Developer:** Manoj Kumar S  

A premium, production-ready, lightweight digital archive and memory CMS for the **BCA Class of 2026**.

---

## 📁 Project Structure

```text
college-memories-26/
├── index.html              # Home Page (Hero, Intro, Stats, Previews, Quotes)
├── timeline.html           # Chronological Visual Timeline Page
├── gallery.html            # Photography Gallery Page (Masonry + Filters + Lightbox)
├── scrapbook.html          # Digital Scrapbook Page (Polaroids + Notes + Tickets)
├── yearbook.html           # Yearbook Page (Student Profile Grid + Live Search)
├── videos.html             # Video Memories Page (Thumbnails + Modal Video Player)
├── about.html              # About Archive & Developer Page
├── css/
│   ├── global.css          # Design system tokens, header, footer, animations, reset
│   ├── home.css            # Home page sections styling
│   ├── timeline.css        # Timeline alternating spine & cards layout
│   ├── gallery.css         # Masonry grid, category buttons, pagination
│   ├── scrapbook.css       # Polaroids, tape strips, handwritten notes, tickets
│   ├── yearbook.css        # Student cards & search bar styling
│   ├── videos.css           # Video cards & responsive video player modal
│   ├── about.css           # About cards & developer bio styling
│   └── responsive.css      # Mobile & desktop media queries (320px - 1920px)
├── js/
│   ├── main.js             # Sticky header, mobile nav drawer, scroll reveals, counters
│   ├── lightbox.js         # Fullscreen universal lightbox (keyboard, swipe, preloader)
│   ├── gallery.js          # Dynamic gallery renderer & filter handler
│   ├── timeline.js         # Dynamic timeline renderer & scroll spine progress line
│   ├── scrapbook.js        # Dynamic scrapbook renderer
│   ├── yearbook.js         # Dynamic student grid renderer & live search
│   └── videos.js           # Dynamic video card renderer & modal controller
├── data/
│   ├── gallery-data.js     # Editable gallery photographs array
│   ├── timeline-data.js    # Editable timeline milestones array
│   ├── scrapbook-data.js   # Editable polaroids, notes & trip tickets array
│   ├── yearbook-data.js    # Editable student profiles array
│   └── video-data.js       # Editable video clips array
└── assets/
    └── images/             # Structured assets for home, gallery, timeline, etc.
```

---

## 🚀 How to Run the Website Locally

Since the website is 100% static:

1. **Option A (Direct File Opening):** Double click any `.html` file (e.g. `index.html`) to open it directly in any modern web browser (Chrome, Firefox, Safari, Edge).
2. **Option B (VS Code Live Server):** Open the project folder in VS Code, right click `index.html`, and click **Open with Live Server**.
3. **Option C (Simple HTTP Server):** Run `npx serve` or `python -m http.server 8000` in the project directory and navigate to `http://localhost:8000`.

---

## ✏️ How to Edit Content

All website content is managed dynamically via human-readable JavaScript data files in the `data/` folder.

### 🖼️ How to Add a New Gallery Photograph

1. Place your photo image file (JPG, PNG, WebP) inside `assets/images/gallery/` (e.g. `my-photo.jpg`).
2. Open `data/gallery-data.js`.
3. Add a new entry to the `GALLERY_DATA` array:

```javascript
{
  id: 25,
  src: "assets/images/gallery/my-photo.jpg",
  title: "Canteen Laughs",
  category: "Friends",
  date: "2025",
  caption: "Sharing a laugh over tea after afternoon lectures.",
  alt: "Group of friends laughing at canteen table"
}
```
4. Save the file and refresh your browser.

---

### 🏷️ How to Create New Gallery Categories

1. Open `data/gallery-data.js` and assign your custom category name (e.g. `"Industrial Visit"`) to any item's `category` property.
2. Open `js/gallery.js` and add `"Industrial Visit"` to the `categories` array in `renderFilterButtons()`:

```javascript
const categories = ['All', 'College Life', 'Classroom', 'Laboratory', 'Friends', 'Culturals', 'Munnar Trip', 'Birthdays', 'Faculty', 'Farewell', 'Industrial Visit'];
```

---

### 📅 How to Add Timeline Events

1. Place event images in `assets/images/timeline/`.
2. Open `data/timeline-data.js` and append a new object to `TIMELINE_DATA`:

```javascript
{
  id: 13,
  year: "2026",
  number: "13",
  title: "Alumni Meet & Reunion",
  date: "December 2026",
  category: "Reunion",
  description: "Returning to campus as proud alumni for our first official batch reunion.",
  quote: "Once a BCA 26 member, always family.",
  images: [
    { src: "assets/images/timeline/reunion.jpg", alt: "Alumni Meet Group Photo" }
  ]
}
```

---

### 🎓 How to Add or Edit Students in Yearbook

1. Place student portrait photo in `assets/images/yearbook/` (e.g. `john-doe.jpg`).
2. Open `data/yearbook-data.js` and append an entry to `YEARBOOK_DATA`:

```javascript
{
  name: "John Doe",
  nickname: "The Visionary",
  image: "assets/images/yearbook/john-doe.jpg",
  quote: "Stay hungry, stay foolish.",
  tag: "Tech Enthusiast"
}
```

---

### 🎥 How to Add Videos

Open `data/video-data.js` and append a new video object to `VIDEO_DATA`:

- **For YouTube:** Use `type: "youtube"` and your YouTube Embed link (`https://www.youtube.com/embed/VIDEO_ID?autoplay=1`).
- **For Google Drive:** Use `type: "gdrive"` and public embed link.
- **For Local MP4:** Use `type: "local"` and file path (`assets/videos/clip.mp4`).

```javascript
{
  id: 7,
  title: "Freshers Day Dance Practice",
  description: "Behind the scenes practice sessions inside the seminar hall.",
  thumbnail: "assets/images/videos/thumb-practice.jpg",
  duration: "03:15",
  category: "Cultural Moments",
  date: "September 2023",
  type: "youtube",
  videoUrl: "https://www.youtube.com/embed/YOUR_YOUTUBE_ID?autoplay=1"
}
```

---

### 🎨 How to Customize Colors & Fonts

Open `css/global.css`. All colors, fonts, shadows, and radii are declared as CSS Variables at the top of the file:

```css
:root {
  --bg-primary: #080808;       /* Primary background */
  --bg-secondary: #111111;     /* Section background */
  --bg-card: #161616;          /* Card background */
  --text-primary: #F5F5F5;     /* Main text */
  --text-secondary: #A9A9A9;   /* Subtitle text */
  --accent-gold: #D7B377;      /* Gold accent color */
  --border-color: rgba(255, 255, 255, 0.10);

  --font-heading: 'Cinzel', serif;
  --font-body: 'Plus Jakarta Sans', sans-serif;
  --font-handwriting: 'Caveat', cursive;
}
```

---

## 🌐 Free Deployment Instructions

### 🐙 Deploying to GitHub Pages (100% Free)

1. Create a public repository on GitHub (e.g., `college-memories-26`).
2. Push all project files to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of College Memories '26 website"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/college-memories-26.git
   git push -u origin main
   ```
3. On GitHub, go to **Settings** → **Pages**.
4. Under **Source**, select **Deploy from a branch** -> Branch: `main` / Folder: `/ (root)`.
5. Click **Save**. Your website will be live in 1-2 minutes at `https://YOUR_USERNAME.github.io/college-memories-26/`.

---

### ⚡ Deploying to Netlify (100% Free)

1. Sign in to [Netlify](https://www.netlify.com/).
2. Click **Add new site** → **Import an existing project** (Connect your GitHub repo), OR drag and drop the entire `college-memories-26` folder into the Netlify Drop area.
3. Build settings can be left blank (as this is a static site).
4. Click **Deploy Site**. Your live URL will be ready instantly.

---

### ☁️ Deploying to Cloudflare Pages (100% Free)

1. Log into your [Cloudflare Dashboard](https://dash.cloudflare.com/).
2. Navigate to **Workers & Pages** → **Create application** → **Pages**.
3. Connect your GitHub repository.
4. Set Framework preset to **None (Static HTML)**.
5. Click **Save and Deploy**.

---

## 🎓 Credit & Attribution

- **Project:** College Memories ’26
- **Tagline:** Three Years. Countless Memories. One Story.
- **Created By:** Manoj Kumar S
- **For:** BCA Class of 2026
