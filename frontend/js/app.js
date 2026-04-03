// ========== KareDefteri App ==========

let currentUser = null;
let currentPage = 'feed';
let feedPage = 1;

// ---- Router ----
function navigate(page, data = {}) {
    currentPage = page;
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));

    // Hide navbar for auth pages
    const navbar = document.getElementById('navbar');
    if (['login', 'register', 'verify'].includes(page)) {
        navbar.style.display = 'none';
    } else {
        navbar.style.display = 'flex';
    }

    switch (page) {
        case 'login': showLogin(); break;
        case 'register': showRegister(); break;
        case 'verify': showVerify(data.email); break;
        case 'feed': showFeed(); break;
        case 'profile': showProfile(data.userId || currentUser?.id); break;
        case 'followers': showFollowersList(data.userId, 'followers'); break;
        case 'following': showFollowersList(data.userId, 'following'); break;
        case 'admin': showAdmin(data.tab); break;
    }
}

// ---- Init ----
async function init() {
    if (api.getToken()) {
        try {
            const res = await api.getMe();
            currentUser = res.user;
            updateNavbar();
            navigate('feed');
        } catch {
            api.setToken(null);
            navigate('login');
        }
    } else {
        navigate('login');
    }
}

function updateNavbar() {
    if (!currentUser) return;
    document.getElementById('nav-username').textContent = currentUser.username;
    const adminBtn = document.getElementById('nav-admin-btn');
    if (adminBtn) {
        adminBtn.style.display = currentUser.role === 'admin' ? 'flex' : 'none';
    }
}

function logout() {
    api.setToken(null);
    currentUser = null;
    navigate('login');
}

// ---- Auth Pages ----
function showLogin() {
    const page = document.getElementById('page-login');
    page.classList.add('active');
    page.innerHTML = `
        <div class="auth-page">
            <div class="auth-card">
                <h1>📷 KareDefteri</h1>
                <p class="subtitle">Anlarınızı karelerle paylaşın</p>
                <div id="login-alert"></div>
                <form id="login-form" onsubmit="handleLogin(event)">
                    <div class="form-group">
                        <label>Kullanıcı Adı veya E-posta</label>
                        <input type="text" class="form-control" id="login-input" placeholder="kullaniciadi veya email@ornek.com" required>
                    </div>
                    <div class="form-group">
                        <label>Şifre</label>
                        <input type="password" class="form-control" id="login-password" placeholder="••••••" required>
                    </div>
                    <button type="submit" class="btn btn-primary" id="login-btn">Giriş Yap</button>
                </form>
                <p class="auth-link">
                    Hesabınız yok mu? <a href="#" onclick="navigate('register')">Kayıt Ol</a>
                </p>
            </div>
        </div>
    `;
}

async function handleLogin(e) {
    e.preventDefault();
    const login = document.getElementById('login-input').value;
    const password = document.getElementById('login-password').value;
    const btn = document.getElementById('login-btn');
    const alertDiv = document.getElementById('login-alert');

    btn.disabled = true;
    btn.textContent = 'Giriş yapılıyor...';

    try {
        const res = await api.login(login, password);
        api.setToken(res.token);
        currentUser = res.user;
        updateNavbar();
        navigate('feed');
    } catch (err) {
        if (err.needs_verification) {
            alertDiv.innerHTML = `<div class="alert alert-info">${err.error}</div>`;
            setTimeout(() => navigate('verify', { email: err.email }), 1500);
        } else {
            alertDiv.innerHTML = `<div class="alert alert-error">${err.error}</div>`;
        }
    }
    btn.disabled = false;
    btn.textContent = 'Giriş Yap';
}

function showRegister() {
    const page = document.getElementById('page-register');
    page.classList.add('active');
    page.innerHTML = `
        <div class="auth-page">
            <div class="auth-card">
                <h1>📷 KareDefteri</h1>
                <p class="subtitle">Yeni hesap oluşturun</p>
                <div id="register-alert"></div>
                <form id="register-form" onsubmit="handleRegister(event)">
                    <div class="form-group">
                        <label>Kullanıcı Adı</label>
                        <input type="text" class="form-control" id="reg-username" placeholder="kullaniciadi" required minlength="3" maxlength="30" pattern="[a-zA-Z0-9_]+">
                    </div>
                    <div class="form-group">
                        <label>E-posta</label>
                        <input type="email" class="form-control" id="reg-email" placeholder="email@ornek.com" required>
                    </div>
                    <div class="form-group">
                        <label>Şifre</label>
                        <input type="password" class="form-control" id="reg-password" placeholder="En az 6 karakter" required minlength="6">
                    </div>
                    <div class="form-group">
                        <label>Ülke</label>
                        <select class="form-control" id="reg-country">
                            <option value="TR">Türkiye</option>
                            <option value="US">Amerika</option>
                            <option value="DE">Almanya</option>
                            <option value="GB">İngiltere</option>
                            <option value="FR">Fransa</option>
                            <option value="NL">Hollanda</option>
                            <option value="AZ">Azerbaycan</option>
                            <option value="OTHER">Diğer</option>
                        </select>
                    </div>
                    <button type="submit" class="btn btn-primary" id="reg-btn">Kayıt Ol</button>
                </form>
                <p class="auth-link">
                    Zaten hesabınız var mı? <a href="#" onclick="navigate('login')">Giriş Yap</a>
                </p>
            </div>
        </div>
    `;
}

async function handleRegister(e) {
    e.preventDefault();
    const data = {
        username: document.getElementById('reg-username').value,
        email: document.getElementById('reg-email').value,
        password: document.getElementById('reg-password').value,
        country: document.getElementById('reg-country').value
    };
    const btn = document.getElementById('reg-btn');
    const alertDiv = document.getElementById('register-alert');

    btn.disabled = true;
    btn.textContent = 'Kayıt oluşturuluyor...';

    try {
        const res = await api.register(data);
        alertDiv.innerHTML = `<div class="alert alert-success">${res.message}</div>`;
        setTimeout(() => navigate('verify', { email: data.email }), 1500);
    } catch (err) {
        alertDiv.innerHTML = `<div class="alert alert-error">${err.error}</div>`;
    }
    btn.disabled = false;
    btn.textContent = 'Kayıt Ol';
}

function showVerify(email) {
    const page = document.getElementById('page-verify');
    page.classList.add('active');
    page.innerHTML = `
        <div class="auth-page">
            <div class="auth-card">
                <h1>📧 Doğrulama</h1>
                <p class="subtitle">E-posta adresinize gönderilen 6 haneli kodu girin</p>
                <div id="verify-alert"></div>
                <form onsubmit="handleVerify(event, '${email}')">
                    <div class="form-group">
                        <label>Doğrulama Kodu</label>
                        <input type="text" class="form-control" id="verify-code" placeholder="123456" required maxlength="6" style="text-align:center;font-size:1.5rem;letter-spacing:0.5rem">
                    </div>
                    <button type="submit" class="btn btn-primary" id="verify-btn">Doğrula</button>
                </form>
                <p class="auth-link" style="margin-top:1rem">
                    <a href="#" onclick="handleResendCode('${email}')">Kodu tekrar gönder</a>
                </p>
                <p class="auth-link">
                    <a href="#" onclick="navigate('login')">Giriş sayfasına dön</a>
                </p>
            </div>
        </div>
    `;
}

async function handleVerify(e, email) {
    e.preventDefault();
    const code = document.getElementById('verify-code').value;
    const btn = document.getElementById('verify-btn');
    const alertDiv = document.getElementById('verify-alert');

    btn.disabled = true;
    try {
        const res = await api.verifyEmail(email, code);
        alertDiv.innerHTML = `<div class="alert alert-success">${res.message}</div>`;
        setTimeout(() => navigate('login'), 1500);
    } catch (err) {
        alertDiv.innerHTML = `<div class="alert alert-error">${err.error}</div>`;
    }
    btn.disabled = false;
}

async function handleResendCode(email) {
    try {
        const res = await api.resendCode(email);
        document.getElementById('verify-alert').innerHTML = `<div class="alert alert-success">${res.message}</div>`;
    } catch (err) {
        document.getElementById('verify-alert').innerHTML = `<div class="alert alert-error">${err.error}</div>`;
    }
}

// ---- Feed Page ----
async function showFeed() {
    const page = document.getElementById('page-feed');
    page.classList.add('active');
    page.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
        const [feedRes, storiesRes] = await Promise.all([
            api.getFeed(1),
            api.getStoriesFeed()
        ]);

        feedPage = 1;
        let html = '';

        // Stories bar
        html += renderStoriesBar(storiesRes.story_groups);

        if (feedRes.posts.length === 0) {
            html += `
                <div class="empty-state">
                    <div class="icon">📷</div>
                    <h3>Henüz gönderi yok</h3>
                    <p>Takip ettiğiniz kişilerin gönderileri burada görünecek.</p>
                    <p style="margin-top:0.5rem">Yeni kişiler keşfetmek için arama yapın!</p>
                </div>
            `;
        } else {
            html += feedRes.posts.map(p => renderFeedPost(p)).join('');
            if (feedRes.pages > 1) {
                html += renderPagination(feedRes.page, feedRes.pages, 'loadFeedPage');
            }
        }

        page.innerHTML = html;
    } catch (err) {
        page.innerHTML = `<div class="alert alert-error">${err.error || 'Bir hata oluştu'}</div>`;
    }
}

async function loadFeedPage(pg) {
    feedPage = pg;
    const page = document.getElementById('page-feed');
    try {
        const feedRes = await api.getFeed(pg);
        // Keep stories bar, replace posts
        const storiesBar = page.querySelector('.stories-bar');
        let html = storiesBar ? storiesBar.outerHTML : '';
        html += feedRes.posts.map(p => renderFeedPost(p)).join('');
        if (feedRes.pages > 1) {
            html += renderPagination(feedRes.page, feedRes.pages, 'loadFeedPage');
        }
        page.innerHTML = html;
        window.scrollTo(0, 0);
    } catch (err) {
        console.error(err);
    }
}

function renderFeedPost(post) {
    const timeAgo = getTimeAgo(post.created_at);
    const likeClass = post.my_reaction === 'like' ? 'liked' : '';
    const dislikeClass = post.my_reaction === 'dislike' ? 'disliked' : '';
    return `
        <div class="feed-post" id="post-${post.id}">
            <div class="feed-post-header">
                <img class="avatar" src="${post.profile_pic || '/assets/default-avatar.svg'}" onerror="this.src='/assets/default-avatar.svg'" alt="">
                <span class="username" onclick="navigate('profile', {userId: ${post.user_id}})">${escapeHtml(post.username)}</span>
                <div class="spacer"></div>
                ${post.user_id === currentUser?.id ? `<button class="action-btn" onclick="deletePost(${post.id})" title="Sil">🗑️</button>` : `<button class="action-btn" onclick="showReportModal(${post.id})" title="Rapor Et">⚑</button>`}
            </div>
            <img class="feed-post-image" src="${post.image_path}" alt="gönderi" loading="lazy">
            <div class="feed-post-actions">
                <button class="action-btn ${likeClass}" onclick="reactToPost(${post.id}, 'like')">
                    ${post.my_reaction === 'like' ? '❤️' : '🤍'} <span class="count">${post.likes}</span>
                </button>
                <button class="action-btn ${dislikeClass}" onclick="reactToPost(${post.id}, 'dislike')">
                    ${post.my_reaction === 'dislike' ? '👎' : '👎🏻'} <span class="count">${post.dislikes}</span>
                </button>
            </div>
            ${post.caption ? `<div class="feed-post-caption"><strong>${escapeHtml(post.username)}</strong> ${escapeHtml(post.caption)}</div>` : ''}
            <div class="feed-post-time">${timeAgo}</div>
        </div>
    `;
}

// ---- Stories ----
function renderStoriesBar(storyGroups) {
    let items = `
        <div class="story-item" onclick="showCreateStoryModal()">
            <div class="story-add">+</div>
            <span class="story-username">Hikaye Ekle</span>
        </div>
    `;
    if (storyGroups) {
        for (const group of storyGroups) {
            const allViewed = group.stories.every(s => s.viewed);
            items += `
                <div class="story-item" onclick="showStoryViewer(${JSON.stringify(group.stories).replace(/"/g, '&quot;')})">
                    <img class="story-avatar ${allViewed ? 'viewed' : ''}" src="${group.profile_pic || '/assets/default-avatar.svg'}" onerror="this.src='/assets/default-avatar.svg'" alt="">
                    <span class="story-username">${escapeHtml(group.username)}</span>
                </div>
            `;
        }
    }
    return `<div class="stories-bar">${items}</div>`;
}

function showStoryViewer(stories) {
    let idx = 0;
    function renderStory() {
        const s = stories[idx];
        document.getElementById('modal-container').innerHTML = `
            <div class="story-modal" onclick="closeModal()">
                <button class="close-btn" onclick="closeModal()">✕</button>
                <img src="${s.image_path}" alt="hikaye" onclick="event.stopPropagation()">
                <div style="position:absolute;bottom:2rem;color:white;text-align:center;width:100%">
                    <strong>${escapeHtml(s.username)}</strong> · ${getTimeAgo(s.created_at)}
                    ${stories.length > 1 ? `<br><small>${idx + 1} / ${stories.length}</small>` : ''}
                </div>
                ${idx > 0 ? `<button style="position:absolute;left:1rem;top:50%;color:white;font-size:2rem;background:none;border:none" onclick="event.stopPropagation();storyNav(-1)">‹</button>` : ''}
                ${idx < stories.length - 1 ? `<button style="position:absolute;right:1rem;top:50%;color:white;font-size:2rem;background:none;border:none" onclick="event.stopPropagation();storyNav(1)">›</button>` : ''}
            </div>
        `;
        api.viewStory(s.id).catch(() => {});
    }
    window.storyNav = function(dir) {
        idx += dir;
        if (idx < 0) idx = 0;
        if (idx >= stories.length) { closeModal(); return; }
        renderStory();
    };
    renderStory();
}

function showCreateStoryModal() {
    document.getElementById('modal-container').innerHTML = `
        <div class="modal-overlay" onclick="closeModal()">
            <div class="modal" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h3>Hikaye Ekle</h3>
                    <button class="modal-close" onclick="closeModal()">✕</button>
                </div>
                <div class="modal-body">
                    <div class="upload-area" onclick="document.getElementById('story-file').click()">
                        <div class="icon">📸</div>
                        <p>Görsel seçmek için tıklayın</p>
                        <input type="file" id="story-file" accept="image/*" style="display:none" onchange="previewStoryImage(this)">
                    </div>
                    <img id="story-preview" class="upload-preview" style="display:none">
                    <div id="story-alert"></div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeModal()">İptal</button>
                    <button class="btn btn-primary" id="story-submit-btn" onclick="submitStory()" disabled>Paylaş</button>
                </div>
            </div>
        </div>
    `;
}

function previewStoryImage(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = e => {
            document.getElementById('story-preview').src = e.target.result;
            document.getElementById('story-preview').style.display = 'block';
            document.getElementById('story-submit-btn').disabled = false;
        };
        reader.readAsDataURL(input.files[0]);
    }
}

async function submitStory() {
    const file = document.getElementById('story-file').files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('image', file);

    const btn = document.getElementById('story-submit-btn');
    btn.disabled = true;
    btn.textContent = 'Yükleniyor...';

    try {
        await api.createStory(formData);
        closeModal();
        showFeed();
    } catch (err) {
        document.getElementById('story-alert').innerHTML = `<div class="alert alert-error">${err.error}</div>`;
        btn.disabled = false;
        btn.textContent = 'Paylaş';
    }
}

// ---- Profile Page ----
async function showProfile(userId) {
    const page = document.getElementById('page-profile');
    page.classList.add('active');
    page.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
        const [userRes, postsRes] = await Promise.all([
            api.getUser(userId),
            api.getUserPosts(userId, 1)
        ]);

        const u = userRes.user;
        const isMe = u.id === currentUser?.id;

        let html = `
            <div class="profile-header">
                <img class="profile-pic" src="${u.profile_pic || '/assets/default-avatar.svg'}" onerror="this.src='/assets/default-avatar.svg'" alt="">
                <div class="profile-info">
                    <h2>
                        ${escapeHtml(u.username)}
                        ${!isMe ? (u.is_following
                            ? `<button class="btn btn-secondary btn-sm" onclick="toggleFollow(${u.id}, true)">Takipten Çık</button>`
                            : `<button class="btn btn-primary btn-sm" onclick="toggleFollow(${u.id}, false)">Takip Et</button>`
                        ) : ''}
                        ${isMe ? `<button class="btn btn-secondary btn-sm" onclick="showCreatePostModal()">+ Gönderi</button>` : ''}
                    </h2>
                    <div class="profile-stats">
                        <span><strong>${u.posts}</strong> gönderi</span>
                        <span style="cursor:pointer" onclick="navigate('followers', {userId: ${u.id}})"><strong>${u.followers}</strong> takipçi</span>
                        <span style="cursor:pointer" onclick="navigate('following', {userId: ${u.id}})"><strong>${u.following}</strong> takip</span>
                    </div>
                    ${u.bio ? `<div class="profile-bio">${escapeHtml(u.bio)}</div>` : ''}
                </div>
            </div>
            <hr class="profile-divider">
        `;

        if (postsRes.posts.length === 0) {
            html += `
                <div class="empty-state">
                    <div class="icon">📷</div>
                    <h3>Henüz gönderi yok</h3>
                    ${isMe ? '<p>İlk gönderinizi paylaşın!</p>' : ''}
                </div>
            `;
        } else {
            html += '<div class="post-grid">';
            for (const p of postsRes.posts) {
                html += `
                    <div class="post-grid-item" onclick="showPostDetail(${p.id})">
                        <img src="${p.image_path}" alt="" loading="lazy">
                        <div class="overlay">
                            <span>❤️ ${p.likes}</span>
                            <span>👎 ${p.dislikes}</span>
                        </div>
                    </div>
                `;
            }
            html += '</div>';
            if (postsRes.pages > 1) {
                html += renderPagination(postsRes.page, postsRes.pages, `loadProfilePosts_${userId}`);
                window[`loadProfilePosts_${userId}`] = (pg) => loadProfilePosts(userId, pg);
            }
        }

        page.innerHTML = html;
    } catch (err) {
        page.innerHTML = `<div class="alert alert-error">${err.error || 'Kullanıcı bulunamadı'}</div>`;
    }
}

async function loadProfilePosts(userId, pg) {
    try {
        const postsRes = await api.getUserPosts(userId, pg);
        const grid = document.querySelector('.post-grid');
        if (grid) {
            grid.innerHTML = postsRes.posts.map(p => `
                <div class="post-grid-item" onclick="showPostDetail(${p.id})">
                    <img src="${p.image_path}" alt="" loading="lazy">
                    <div class="overlay">
                        <span>❤️ ${p.likes}</span>
                        <span>👎 ${p.dislikes}</span>
                    </div>
                </div>
            `).join('');
        }
    } catch (err) {
        console.error(err);
    }
}

async function toggleFollow(userId, isFollowing) {
    try {
        if (isFollowing) {
            await api.unfollow(userId);
        } else {
            await api.follow(userId);
        }
        showProfile(userId);
    } catch (err) {
        alert(err.error);
    }
}

// ---- Post Detail ----
async function showPostDetail(postId) {
    try {
        const res = await api.getPost(postId);
        const p = res.post;
        const isOwner = p.user_id === currentUser?.id;

        document.getElementById('modal-container').innerHTML = `
            <div class="modal-overlay" onclick="closeModal()">
                <div class="modal modal-wide" onclick="event.stopPropagation()">
                    <div class="post-detail">
                        <div class="post-detail-image">
                            <img src="${p.image_path}" alt="">
                        </div>
                        <div class="post-detail-info">
                            <div class="feed-post-header" style="border-bottom: 1px solid var(--gray-400)">
                                <img class="avatar" src="${p.profile_pic || '/assets/default-avatar.svg'}" onerror="this.src='/assets/default-avatar.svg'" alt="">
                                <span class="username" onclick="closeModal();navigate('profile',{userId:${p.user_id}})">${escapeHtml(p.username)}</span>
                                <div class="spacer"></div>
                                <button class="modal-close" onclick="closeModal()">✕</button>
                            </div>
                            <div style="flex:1;padding:1rem;overflow-y:auto">
                                ${p.caption ? `<p><strong>${escapeHtml(p.username)}</strong> ${escapeHtml(p.caption)}</p>` : '<p style="color:var(--gray-500)">Açıklama yok</p>'}
                            </div>
                            <div style="border-top:1px solid var(--gray-400);padding:0.8rem 1rem">
                                <div class="feed-post-actions" style="padding:0">
                                    <button class="action-btn ${p.my_reaction === 'like' ? 'liked' : ''}" onclick="reactToPostDetail(${p.id}, 'like')">
                                        ${p.my_reaction === 'like' ? '❤️' : '🤍'} <span class="count" id="detail-likes-${p.id}">${p.likes}</span>
                                    </button>
                                    <button class="action-btn ${p.my_reaction === 'dislike' ? 'disliked' : ''}" onclick="reactToPostDetail(${p.id}, 'dislike')">
                                        ${p.my_reaction === 'dislike' ? '👎' : '👎🏻'} <span class="count" id="detail-dislikes-${p.id}">${p.dislikes}</span>
                                    </button>
                                    <div class="spacer"></div>
                                    ${!isOwner ? `<button class="action-btn" onclick="showReportModal(${p.id})">⚑ Rapor Et</button>` : ''}
                                    ${isOwner ? `<button class="action-btn" onclick="deletePost(${p.id});closeModal()">🗑️ Sil</button>` : ''}
                                </div>
                                <div class="feed-post-time">${getTimeAgo(p.created_at)}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    } catch (err) {
        alert(err.error || 'Gönderi yüklenemedi');
    }
}

// ---- Create Post Modal ----
function showCreatePostModal() {
    document.getElementById('modal-container').innerHTML = `
        <div class="modal-overlay" onclick="closeModal()">
            <div class="modal" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h3>Yeni Gönderi</h3>
                    <button class="modal-close" onclick="closeModal()">✕</button>
                </div>
                <div class="modal-body">
                    <div class="upload-area" onclick="document.getElementById('post-file').click()">
                        <div class="icon">📸</div>
                        <p>Görsel seçmek için tıklayın</p>
                        <input type="file" id="post-file" accept="image/*" style="display:none" onchange="previewPostImage(this)">
                    </div>
                    <img id="post-preview" class="upload-preview" style="display:none">
                    <div class="form-group">
                        <label>Açıklama (isteğe bağlı)</label>
                        <textarea class="form-control" id="post-caption" placeholder="Bir şeyler yazın..." rows="3"></textarea>
                    </div>
                    <div id="post-alert"></div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeModal()">İptal</button>
                    <button class="btn btn-primary" id="post-submit-btn" onclick="submitPost()" disabled>Paylaş</button>
                </div>
            </div>
        </div>
    `;
}

function previewPostImage(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = e => {
            document.getElementById('post-preview').src = e.target.result;
            document.getElementById('post-preview').style.display = 'block';
            document.getElementById('post-submit-btn').disabled = false;
        };
        reader.readAsDataURL(input.files[0]);
    }
}

async function submitPost() {
    const file = document.getElementById('post-file').files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('image', file);
    formData.append('caption', document.getElementById('post-caption').value);

    const btn = document.getElementById('post-submit-btn');
    btn.disabled = true;
    btn.textContent = 'Yükleniyor...';

    try {
        await api.createPost(formData);
        closeModal();
        navigate('profile', { userId: currentUser.id });
    } catch (err) {
        document.getElementById('post-alert').innerHTML = `<div class="alert alert-error">${err.error}</div>`;
        btn.disabled = false;
        btn.textContent = 'Paylaş';
    }
}

// ---- Reactions ----
async function reactToPost(postId, reaction) {
    try {
        const res = await api.reactPost(postId, reaction);
        const postEl = document.getElementById(`post-${postId}`);
        if (postEl) {
            const btns = postEl.querySelectorAll('.action-btn');
            // Refresh the feed post inline
            const likeBtn = btns[0];
            const dislikeBtn = btns[1];
            likeBtn.className = `action-btn ${res.my_reaction === 'like' ? 'liked' : ''}`;
            likeBtn.innerHTML = `${res.my_reaction === 'like' ? '❤️' : '🤍'} <span class="count">${res.likes}</span>`;
            dislikeBtn.className = `action-btn ${res.my_reaction === 'dislike' ? 'disliked' : ''}`;
            dislikeBtn.innerHTML = `${res.my_reaction === 'dislike' ? '👎' : '👎🏻'} <span class="count">${res.dislikes}</span>`;
        }
    } catch (err) {
        console.error(err);
    }
}

async function reactToPostDetail(postId, reaction) {
    try {
        const res = await api.reactPost(postId, reaction);
        // Re-render detail modal
        showPostDetail(postId);
    } catch (err) {
        console.error(err);
    }
}

async function deletePost(postId) {
    if (!confirm('Bu gönderiyi silmek istediğinize emin misiniz?')) return;
    try {
        await api.deletePost(postId);
        const el = document.getElementById(`post-${postId}`);
        if (el) el.remove();
        else navigate('profile', { userId: currentUser.id });
    } catch (err) {
        alert(err.error);
    }
}

// ---- Report Modal ----
function showReportModal(postId) {
    document.getElementById('modal-container').innerHTML = `
        <div class="modal-overlay" onclick="closeModal()">
            <div class="modal" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h3>Gönderiyi Rapor Et</h3>
                    <button class="modal-close" onclick="closeModal()">✕</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>Raporlama Sebebi</label>
                        <select class="form-control" id="report-reason">
                            <option value="Uygunsuz içerik">Uygunsuz içerik</option>
                            <option value="Spam">Spam</option>
                            <option value="Nefret söylemi">Nefret söylemi</option>
                            <option value="Şiddet içerik">Şiddet içerik</option>
                            <option value="Diğer">Diğer</option>
                        </select>
                    </div>
                    <div id="report-alert"></div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeModal()">İptal</button>
                    <button class="btn btn-danger" onclick="submitReport(${postId})">Rapor Et</button>
                </div>
            </div>
        </div>
    `;
}

async function submitReport(postId) {
    const reason = document.getElementById('report-reason').value;
    try {
        await api.reportPost(postId, reason);
        document.getElementById('report-alert').innerHTML = `<div class="alert alert-success">Gönderi raporlandı!</div>`;
        setTimeout(closeModal, 1000);
    } catch (err) {
        document.getElementById('report-alert').innerHTML = `<div class="alert alert-error">${err.error}</div>`;
    }
}

// ---- Followers / Following List ----
async function showFollowersList(userId, type) {
    const page = document.getElementById('page-followers');
    page.classList.add('active');
    page.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
        const res = type === 'followers' ? await api.getFollowers(userId) : await api.getFollowing(userId);
        const list = type === 'followers' ? res.followers : res.following;
        const title = type === 'followers' ? 'Takipçiler' : 'Takip Edilenler';

        let html = `<h2 style="margin-bottom:1rem">${title}</h2>`;
        html += `<p style="margin-bottom:1rem"><a href="#" onclick="navigate('profile', {userId: ${userId}})">← Profile dön</a></p>`;

        if (list.length === 0) {
            html += `<div class="empty-state"><p>${type === 'followers' ? 'Henüz takipçi yok' : 'Henüz kimseyi takip etmiyor'}</p></div>`;
        } else {
            for (const u of list) {
                html += `
                    <div class="user-list-item">
                        <img class="avatar" src="${u.profile_pic || '/assets/default-avatar.svg'}" onerror="this.src='/assets/default-avatar.svg'" alt="">
                        <div class="info">
                            <div class="name" onclick="navigate('profile', {userId: ${u.id}})">${escapeHtml(u.username)}</div>
                            ${u.bio ? `<div class="bio">${escapeHtml(u.bio)}</div>` : ''}
                        </div>
                        ${u.id !== currentUser?.id ? `
                            <button class="btn btn-sm ${u.im_following ? 'btn-secondary' : 'btn-primary'}" onclick="toggleFollow(${u.id}, ${u.im_following})">
                                ${u.im_following ? 'Takipten Çık' : 'Takip Et'}
                            </button>
                        ` : ''}
                    </div>
                `;
            }
        }

        page.innerHTML = html;
    } catch (err) {
        page.innerHTML = `<div class="alert alert-error">${err.error || 'Hata oluştu'}</div>`;
    }
}

// ---- Search ----
let searchTimeout;
function handleSearch(input) {
    clearTimeout(searchTimeout);
    const q = input.value.trim();
    const dropdown = document.getElementById('search-dropdown');

    if (q.length < 2) {
        dropdown.style.display = 'none';
        return;
    }

    searchTimeout = setTimeout(async () => {
        try {
            const res = await api.searchUsers(q);
            if (res.users.length === 0) {
                dropdown.innerHTML = '<div style="padding:1rem;color:var(--gray-600)">Sonuç bulunamadı</div>';
            } else {
                dropdown.innerHTML = res.users.map(u => `
                    <div class="search-result-item" onclick="document.getElementById('search-dropdown').style.display='none';document.getElementById('search-input').value='';navigate('profile',{userId:${u.id}})">
                        <img src="${u.profile_pic || '/assets/default-avatar.svg'}" onerror="this.src='/assets/default-avatar.svg'" alt="">
                        <div>
                            <strong>${escapeHtml(u.username)}</strong>
                            ${u.bio ? `<br><small style="color:var(--gray-600)">${escapeHtml(u.bio.substring(0, 40))}</small>` : ''}
                        </div>
                    </div>
                `).join('');
            }
            dropdown.style.display = 'block';
        } catch {
            dropdown.style.display = 'none';
        }
    }, 300);
}

// ---- Admin Panel ----
async function showAdmin(tab = 'stats') {
    if (currentUser?.role !== 'admin') {
        navigate('feed');
        return;
    }

    const page = document.getElementById('page-admin');
    page.classList.add('active');

    page.innerHTML = `
        <div class="admin-layout">
            <div class="admin-sidebar">
                <div class="admin-sidebar-item ${tab === 'stats' ? 'active' : ''}" onclick="navigate('admin', {tab:'stats'})">📊 <span>İstatistikler</span></div>
                <div class="admin-sidebar-item ${tab === 'reports' ? 'active' : ''}" onclick="navigate('admin', {tab:'reports'})">⚑ <span>Raporlar</span></div>
                <div class="admin-sidebar-item ${tab === 'users' ? 'active' : ''}" onclick="navigate('admin', {tab:'users'})">👥 <span>Kullanıcılar</span></div>
            </div>
            <div class="admin-content" id="admin-content">
                <div class="loading"><div class="spinner"></div></div>
            </div>
        </div>
    `;

    switch (tab) {
        case 'stats': await loadAdminStats(); break;
        case 'reports': await loadAdminReports(); break;
        case 'users': await loadAdminUsers(); break;
    }
}

async function loadAdminStats() {
    try {
        const res = await api.getAdminStats();
        const s = res.stats;
        const content = document.getElementById('admin-content');

        let html = '<h2 style="margin-bottom:1rem">Sistem İstatistikleri</h2>';
        html += `
            <div class="stat-cards">
                <div class="stat-card"><div class="label">Toplam Kullanıcı</div><div class="value">${s.total_users}</div></div>
                <div class="stat-card"><div class="label">Aktif Kullanıcı</div><div class="value" style="color:var(--success)">${s.active_users}</div></div>
                <div class="stat-card"><div class="label">Yasaklı Kullanıcı</div><div class="value" style="color:var(--danger)">${s.banned_users}</div></div>
                <div class="stat-card"><div class="label">Doğrulanmamış</div><div class="value" style="color:var(--warning)">${s.inactive_users}</div></div>
                <div class="stat-card"><div class="label">Toplam Gönderi</div><div class="value">${s.total_posts}</div></div>
                <div class="stat-card"><div class="label">Görünür Gönderi</div><div class="value">${s.visible_posts}</div></div>
                <div class="stat-card"><div class="label">Gizli Gönderi</div><div class="value">${s.hidden_posts}</div></div>
                <div class="stat-card"><div class="label">Bekleyen Rapor</div><div class="value" style="color:var(--danger)">${s.pending_reports}</div></div>
            </div>
        `;

        if (s.country_distribution.length > 0) {
            html += '<h3 style="margin:1.5rem 0 1rem">Ülke Dağılımı</h3>';
            html += '<div class="admin-table"><table><tr><th>Ülke</th><th>Kullanıcı Sayısı</th></tr>';
            for (const c of s.country_distribution) {
                html += `<tr><td>${escapeHtml(c.country)}</td><td>${c.count}</td></tr>`;
            }
            html += '</table></div>';
        }

        content.innerHTML = html;
    } catch (err) {
        document.getElementById('admin-content').innerHTML = `<div class="alert alert-error">${err.error}</div>`;
    }
}

async function loadAdminReports(status = 'pending', page = 1) {
    try {
        const res = await api.getAdminReports(status, page);
        const content = document.getElementById('admin-content');

        let html = '<h2 style="margin-bottom:1rem">Raporlanan Gönderiler</h2>';
        html += `
            <div style="margin-bottom:1rem;display:flex;gap:0.5rem">
                <button class="btn btn-sm ${status === 'pending' ? 'btn-primary' : 'btn-secondary'}" onclick="loadAdminReports('pending')">Bekleyen</button>
                <button class="btn btn-sm ${status === 'reviewed' ? 'btn-primary' : 'btn-secondary'}" onclick="loadAdminReports('reviewed')">İncelenen</button>
                <button class="btn btn-sm ${status === 'dismissed' ? 'btn-primary' : 'btn-secondary'}" onclick="loadAdminReports('dismissed')">Reddedilen</button>
            </div>
        `;

        if (res.reports.length === 0) {
            html += '<div class="empty-state"><p>Rapor bulunamadı</p></div>';
        } else {
            html += '<div class="admin-table"><table><tr><th>Görsel</th><th>Gönderi Sahibi</th><th>Raporlayan</th><th>Sebep</th><th>Toplam Rapor</th><th>Durum</th><th>İşlem</th></tr>';
            for (const r of res.reports) {
                html += `
                    <tr>
                        <td><img src="${r.image_path}" style="width:60px;height:60px;object-fit:cover;border-radius:4px" alt=""></td>
                        <td>${escapeHtml(r.post_owner_username)}</td>
                        <td>${escapeHtml(r.reporter_username)}</td>
                        <td>${escapeHtml(r.reason)}</td>
                        <td><span class="badge badge-warning">${r.total_reports}</span></td>
                        <td><span class="badge ${r.is_visible ? 'badge-success' : 'badge-danger'}">${r.is_visible ? 'Görünür' : 'Gizli'}</span></td>
                        <td style="display:flex;gap:0.3rem;flex-wrap:wrap">
                            ${r.is_visible ? `<button class="btn btn-danger btn-sm" onclick="adminTogglePost(${r.post_id})">Gizle</button>` : `<button class="btn btn-success btn-sm" onclick="adminTogglePost(${r.post_id})">Göster</button>`}
                            ${status === 'pending' ? `<button class="btn btn-secondary btn-sm" onclick="adminReviewReport(${r.id}, 'dismissed')">Reddet</button>` : ''}
                        </td>
                    </tr>
                `;
            }
            html += '</table></div>';
        }

        content.innerHTML = html;
    } catch (err) {
        document.getElementById('admin-content').innerHTML = `<div class="alert alert-error">${err.error}</div>`;
    }
}

async function loadAdminUsers(page = 1, q = '') {
    try {
        const res = await api.getAdminUsers(page, q);
        const content = document.getElementById('admin-content');

        let html = '<h2 style="margin-bottom:1rem">Kullanıcı Yönetimi</h2>';
        html += `
            <div style="margin-bottom:1rem">
                <input type="text" class="form-control" placeholder="Kullanıcı ara..." value="${escapeHtml(q)}"
                    onkeyup="if(event.key==='Enter')loadAdminUsers(1,this.value)" style="max-width:300px">
            </div>
        `;

        if (res.users.length === 0) {
            html += '<div class="empty-state"><p>Kullanıcı bulunamadı</p></div>';
        } else {
            html += '<div class="admin-table"><table><tr><th>ID</th><th>Kullanıcı</th><th>E-posta</th><th>Ülke</th><th>Gönderi</th><th>Rapor</th><th>Durum</th><th>İşlem</th></tr>';
            for (const u of res.users) {
                const statusBadge = u.is_banned ? '<span class="badge badge-danger">Yasaklı</span>'
                    : u.is_active ? '<span class="badge badge-success">Aktif</span>'
                    : '<span class="badge badge-warning">Doğrulanmamış</span>';
                html += `
                    <tr>
                        <td>${u.id}</td>
                        <td><strong>${escapeHtml(u.username)}</strong></td>
                        <td>${escapeHtml(u.email)}</td>
                        <td>${escapeHtml(u.country)}</td>
                        <td>${u.post_count}</td>
                        <td>${u.report_count > 0 ? `<span class="badge badge-warning">${u.report_count}</span>` : '0'}</td>
                        <td>${statusBadge}</td>
                        <td>
                            ${u.is_banned
                                ? `<button class="btn btn-success btn-sm" onclick="adminUnbanUser(${u.id})">Yasağı Kaldır</button>`
                                : `<button class="btn btn-danger btn-sm" onclick="showBanModal(${u.id}, '${escapeHtml(u.username)}')">Yasakla</button>`
                            }
                        </td>
                    </tr>
                `;
            }
            html += '</table></div>';
        }

        content.innerHTML = html;
    } catch (err) {
        document.getElementById('admin-content').innerHTML = `<div class="alert alert-error">${err.error}</div>`;
    }
}

async function adminTogglePost(postId) {
    try {
        await api.togglePostVisibility(postId);
        loadAdminReports();
    } catch (err) {
        alert(err.error);
    }
}

async function adminReviewReport(reportId, action) {
    try {
        await api.reviewReport(reportId, action);
        loadAdminReports();
    } catch (err) {
        alert(err.error);
    }
}

function showBanModal(userId, username) {
    document.getElementById('modal-container').innerHTML = `
        <div class="modal-overlay" onclick="closeModal()">
            <div class="modal" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h3>${username} kullanıcısını yasakla</h3>
                    <button class="modal-close" onclick="closeModal()">✕</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>Yasaklama Sebebi</label>
                        <textarea class="form-control" id="ban-reason" placeholder="Yasaklama sebebini yazın..."></textarea>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeModal()">İptal</button>
                    <button class="btn btn-danger" onclick="adminBanUser(${userId})">Yasakla</button>
                </div>
            </div>
        </div>
    `;
}

async function adminBanUser(userId) {
    const reason = document.getElementById('ban-reason').value || 'Kural ihlali';
    try {
        await api.banUser(userId, reason);
        closeModal();
        loadAdminUsers();
    } catch (err) {
        alert(err.error);
    }
}

async function adminUnbanUser(userId) {
    if (!confirm('Bu kullanıcının yasağını kaldırmak istediğinize emin misiniz?')) return;
    try {
        await api.unbanUser(userId);
        loadAdminUsers();
    } catch (err) {
        alert(err.error);
    }
}

// ---- Helpers ----
function closeModal() {
    document.getElementById('modal-container').innerHTML = '';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getTimeAgo(dateStr) {
    const date = new Date(dateStr + 'Z');
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);

    if (diff < 60) return 'az önce';
    if (diff < 3600) return `${Math.floor(diff / 60)} dakika önce`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} saat önce`;
    if (diff < 604800) return `${Math.floor(diff / 86400)} gün önce`;
    return date.toLocaleDateString('tr-TR');
}

function renderPagination(current, total, funcName) {
    let html = '<div class="pagination">';
    if (current > 1) {
        html += `<button onclick="${funcName}(${current - 1})">‹ Önceki</button>`;
    }
    for (let i = Math.max(1, current - 2); i <= Math.min(total, current + 2); i++) {
        html += `<button class="${i === current ? 'active' : ''}" onclick="${funcName}(${i})">${i}</button>`;
    }
    if (current < total) {
        html += `<button onclick="${funcName}(${current + 1})">Sonraki ›</button>`;
    }
    html += '</div>';
    return html;
}

// Close search dropdown on click outside
document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('search-dropdown');
    if (dropdown && !e.target.closest('.nav-search-wrapper')) {
        dropdown.style.display = 'none';
    }
});

// Init on load
document.addEventListener('DOMContentLoaded', init);
