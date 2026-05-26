let supabaseClient = null;
let currentUser = null;
let currentBook = null;
let bookInstance = null;
let rendition = null;
let fontScale = 100;
let darkTheme = false;

async function getSupabase() {
  if (supabaseClient) return supabaseClient;
  const { createClient } = await import("https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm");
  const url = window.APP_CONFIG?.supabaseUrl;
  const key = window.APP_CONFIG?.supabaseAnonKey;
  if (!url || !key) throw new Error("Missing Supabase frontend config");
  supabaseClient = createClient(url, key);
  return supabaseClient;
}

async function getAccessToken() {
  const supabase = await getSupabase();
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token || null;
}

async function authFetch(url, options = {}) {
  const token = await getAccessToken();
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(url, { ...options, headers });
}

function setMessage(id, message, isError = false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = message || "";
  el.classList.toggle("error", isError);
}

function setSignedInUI(user) {
  document.getElementById("login-panel").hidden = !!user;
  document.getElementById("user-panel").hidden = !user;
  document.getElementById("auth-status").textContent = user ? `Signed in as ${user.email}` : "Signed out";
  if (!user) {
    document.getElementById("book-list").innerHTML = '<div class="empty-state small-empty"><p>Sign in to see your books.</p></div>';
    document.getElementById("continue-reading").innerHTML = "<p>No recent book yet.</p>";
  }
}

async function signInWithEmail(email) {
  const supabase = await getSupabase();
  const redirectTo = `${window.location.origin}/app/`;
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: { emailRedirectTo: redirectTo }
  });
  if (error) throw error;
}

async function signOut() {
  const supabase = await getSupabase();
  await supabase.auth.signOut();
  currentUser = null;
  setSignedInUI(null);
}

async function refreshAuthStatus() {
  const supabase = await getSupabase();
  const { data } = await supabase.auth.getUser();
  currentUser = data.user || null;
  setSignedInUI(currentUser);
}

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, function(char) {
    return ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    })[char];
  });
}

function renderContinueReading(books) {
  const target = document.getElementById("continue-reading");
  if (!books.length) {
    target.innerHTML = "<p>No recent book yet.</p>";
    return;
  }
  const book = books[0];
  target.innerHTML = `
    <button class="book-card" type="button" data-book-open="${book.id}">
      <strong>${escapeHtml(book.title)}</strong>
      <span>${escapeHtml(book.author || "Unknown author")}</span>
      <div class="progress-bar"><div class="progress-fill" style="width:${Math.round(book.progress || 0)}%"></div></div>
      <div class="meta-row">
        <span>${Math.round(book.progress || 0)}% read</span>
        <span>Continue</span>
      </div>
    </button>
  `;
  target.querySelector("[data-book-open]")?.addEventListener("click", () => openBook(book.id));
}

function renderBooks(books) {
  const container = document.getElementById("book-list");
  if (!books.length) {
    container.innerHTML = '<div class="empty-state small-empty"><p>No books yet. Upload one above.</p></div>';
    renderContinueReading([]);
    return;
  }

  renderContinueReading(books);

  container.innerHTML = books.map(book => `
    <button class="book-card" type="button" data-book-id="${book.id}">
      <strong>${escapeHtml(book.title)}</strong>
      <span>${escapeHtml(book.author || "Unknown author")}</span>
      <div class="progress-bar"><div class="progress-fill" style="width:${Math.round(book.progress || 0)}%"></div></div>
      <div class="meta-row">
        <span>${Math.round(book.progress || 0)}%</span>
        <span>${book.epub_file_url ? "Uploaded" : "Missing file"}</span>
      </div>
    </button>
  `).join("");

  container.querySelectorAll("[data-book-id]").forEach(button => {
    button.addEventListener("click", () => openBook(button.dataset.bookId));
  });
}

async function loadBooks() {
  const res = await authFetch("/api/books/");
  if (!res.ok) {
    setMessage("login-message", "You need to sign in first.", true);
    return;
  }
  const books = await res.json();
  renderBooks(books);
}

async function uploadBook(event) {
  event.preventDefault();

  const form = event.currentTarget;
  const formData = new FormData(form);

  const file = formData.get("epub_file");
  if (!(file instanceof File) || !file.name) {
    setMessage("upload-message", "Please choose an EPUB file.", true);
    return;
  }

  if (!file.name.toLowerCase().endsWith(".epub")) {
    setMessage("upload-message", "Only .epub files are allowed.", true);
    return;
  }

  setMessage("upload-message", "Uploading EPUB...");

  const res = await authFetch("/api/books/", {
    method: "POST",
    body: formData
  });

  if (!res.ok) {
    let detail = "Upload failed.";
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch (error) {}
    setMessage("upload-message", detail, true);
    return;
  }

  setMessage("upload-message", "Upload complete.");
  form.reset();
  await loadBooks();
}

function renderToc(toc) {
  const target = document.getElementById("toc-list");
  if (!toc.length) {
    target.innerHTML = "<p class='muted'>No table of contents found.</p>";
    return;
  }

  target.innerHTML = toc.map((item, index) => `
    <button class="toc-item" type="button" data-toc-index="${index}">
      ${escapeHtml(item.label || item.href || `Section ${index + 1}`)}
    </button>
  `).join("");

  target.querySelectorAll("[data-toc-index]").forEach(btn => {
    btn.addEventListener("click", () => {
      const index = Number(btn.dataset.tocIndex);
      const item = toc[index];
      if (item && rendition) rendition.display(item.href);
    });
  });
}

function renderBookmarks(items) {
  const target = document.getElementById("bookmark-list");
  if (!items.length) {
    target.innerHTML = "<p class='muted'>No bookmarks yet.</p>";
    return;
  }
  target.innerHTML = items.map(item => `
    <div class="mini-item">
      <strong>${escapeHtml(item.label || "Saved bookmark")}</strong>
      <div class="meta-row"><span>${new Date(item.created_at).toLocaleString()}</span></div>
    </div>
  `).join("");
}

function renderNotes(items) {
  const target = document.getElementById("note-list");
  if (!items.length) {
    target.innerHTML = "<p class='muted'>No notes yet.</p>";
    return;
  }
  target.innerHTML = items.map(item => `
    <div class="mini-item">
      <div class="note-quote">${escapeHtml(item.quote || "No quote")}</div>
      <strong>${escapeHtml(item.body || "Untitled note")}</strong>
      <div class="meta-row"><span>${new Date(item.created_at).toLocaleString()}</span></div>
    </div>
  `).join("");
}

async function loadBookmarks(bookId) {
  const res = await authFetch(`/api/books/${bookId}/bookmarks/`);
  if (!res.ok) return;
  renderBookmarks(await res.json());
}

async function loadNotes(bookId) {
  const res = await authFetch(`/api/books/${bookId}/notes/`);
  if (!res.ok) return;
  renderNotes(await res.json());
}

function applyReaderTheme() {
  document.documentElement.setAttribute("data-theme", darkTheme ? "dark" : "light");
  if (rendition && rendition.themes) {
    rendition.themes.default({
      body: {
        "background": darkTheme ? "#1b1a18" : "#fffdf9",
        "color": darkTheme ? "#ece6dd" : "#211d17",
        "font-size": `${fontScale}%`,
        "line-height": "1.7"
      }
    });
  }
}

async function saveProgress(location) {
  if (!currentBook || !location || !location.start) return;
  const cfi = location.start.cfi || "";
  const current = location.start.displayed;
  const percent = current && current.total ? (current.page / current.total) * 100 : 0;
  const chapterLabel = location.start.href || "";

  await authFetch(`/api/books/${currentBook.id}/progress/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      cfi,
      chapter_label: chapterLabel,
      percent
    })
  });
}

function attachRenditionEvents() {
  rendition.on("relocated", async (location) => {
    await saveProgress(location);
  });

  rendition.on("rendered", () => {
    applyReaderTheme();
  });
}

async function openBook(bookId) {
  const detailRes = await authFetch(`/api/books/${bookId}/`);
  if (!detailRes.ok) {
    setMessage("upload-message", "Could not load book details.", true);
    return;
  }

  const book = await detailRes.json();
  currentBook = book;

  document.getElementById("active-book-title").textContent = book.title;
  document.getElementById("active-book-author").textContent = book.author || "Unknown author";

  await loadBookmarks(bookId);
  await loadNotes(bookId);

  const loading = document.getElementById("reader-loading");
  const viewer = document.getElementById("viewer");

  if (!book.epub_file_url) {
    loading.hidden = false;
    viewer.hidden = true;
    loading.innerHTML = "<p>This book does not have an uploaded EPUB file yet.</p>";
    return;
  }

  loading.hidden = true;
  viewer.hidden = false;
  viewer.innerHTML = "";

  bookInstance = ePub(book.epub_file_url);
  rendition = bookInstance.renderTo("viewer", {
    width: "100%",
    height: "100%"
  });

  attachRenditionEvents();

  try {
    const navigation = await bookInstance.loaded.navigation;
    renderToc(navigation.toc || []);
  } catch (error) {
    renderToc([]);
  }

  try {
    await rendition.display(book.progress?.cfi || undefined);
  } catch (error) {
    await rendition.display();
  }

  applyReaderTheme();
}

async function addBookmark() {
  if (!currentBook || !rendition || !rendition.currentLocation()) return;
  const location = rendition.currentLocation();
  const cfi = location.start?.cfi || "";
  const label = currentBook.title + " bookmark";

  const res = await authFetch(`/api/books/${currentBook.id}/bookmarks/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cfi, label })
  });

  if (res.ok) await loadBookmarks(currentBook.id);
}

async function addNote() {
  if (!currentBook || !rendition || !rendition.currentLocation()) return;
  const body = window.prompt("Write your note");
  if (!body) return;

  const location = rendition.currentLocation();
  const cfi = location.start?.cfi || "";
  const quote = location.start?.href || "";

  const res = await authFetch(`/api/books/${currentBook.id}/notes/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cfi, quote, body })
  });

  if (res.ok) await loadNotes(currentBook.id);
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const email = form.email.value.trim();

  if (!email) {
    setMessage("login-message", "Please enter your email.", true);
    return;
  }

  setMessage("login-message", "Sending magic link...");
  try {
    await signInWithEmail(email);
    setMessage("login-message", "Magic link sent. Check your inbox.");
    form.reset();
  } catch (error) {
    setMessage("login-message", error.message || "Sign-in failed.", true);
  }
}

function bindUI() {
  document.getElementById("login-form").addEventListener("submit", handleLoginSubmit);
  document.getElementById("upload-form").addEventListener("submit", uploadBook);
  document.getElementById("sign-out-btn").addEventListener("click", signOut);
  document.getElementById("load-books-btn").addEventListener("click", loadBooks);
  document.getElementById("theme-btn").addEventListener("click", () => {
    darkTheme = !darkTheme;
    applyReaderTheme();
  });
  document.getElementById("font-plus-btn").addEventListener("click", () => {
    fontScale = Math.min(fontScale + 10, 180);
    applyReaderTheme();
  });
  document.getElementById("font-minus-btn").addEventListener("click", () => {
    fontScale = Math.max(fontScale - 10, 70);
    applyReaderTheme();
  });
  document.getElementById("bookmark-btn").addEventListener("click", addBookmark);
  document.getElementById("note-btn").addEventListener("click", addNote);
}

async function init() {
  bindUI();
  await refreshAuthStatus();
  if (currentUser) await loadBooks();

  const supabase = await getSupabase();
  supabase.auth.onAuthStateChange(async () => {
    await refreshAuthStatus();
    if (currentUser) await loadBooks();
  });
}

init();
