/**
 * VISCOM — Instagram Profile Analyzer
 * Frontend Application Logic
 */

let charts = {};

// ── Analyze Handler ──
async function analyze() {
  const username = document.getElementById('username-input').value.trim().replace('@', '');
  if (!username) {
    showToast('Please enter a username');
    return;
  }

  const btn = document.getElementById('analyze-btn');
  const loading = document.getElementById('loading');
  const loadingText = document.getElementById('loading-text');
  const results = document.getElementById('results');

  // Show loading
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Analyzing...';
  loading.style.display = 'flex';
  results.style.display = 'none';

  const steps = [
    'Connecting to Instagram...',
    'Scraping profile data...',
    'Analyzing engagement...',
    'Processing hashtags...',
    'Generating insights...',
    'Building dashboard...',
  ];

  let stepIdx = 0;
  const stepInterval = setInterval(() => {
    if (stepIdx < steps.length) {
      loadingText.textContent = steps[stepIdx];
      stepIdx++;
    }
  }, 800);

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, max_posts: 30 }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Analysis failed');
    }

    clearInterval(stepInterval);
    loading.style.display = 'none';
    renderDashboard(data);

  } catch (err) {
    clearInterval(stepInterval);
    loading.style.display = 'none';
    showToast(err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Analyze';
  }
}

// ── Render Full Dashboard ──
function renderDashboard(data) {
  const results = document.getElementById('results');
  results.style.display = 'block';

  // Destroy old charts
  Object.values(charts).forEach(c => c.destroy());
  charts = {};

  renderProfileHeader(data.profile);
  renderStats(data.engagement, data.profile);
  renderEngagementChart(data.engagement);
  renderContentChart(data.content_types);
  renderDayChart(data.posting_patterns);
  renderHourChart(data.posting_patterns);
  renderHashtags(data.hashtags);
  renderCaptionAnalysis(data.caption_analysis);
  renderTopBottomPosts(data.top_bottom_posts);
  renderRecommendations(data.recommendations);
  renderPostingSummary(data.posting_patterns);

  // Scroll to results
  setTimeout(() => {
    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 200);
}

// ── Profile Header ──
function renderProfileHeader(profile) {
  const container = document.getElementById('profile-header');
  const verifiedBadge = profile.is_verified
    ? '<span class="badge badge-blue" style="margin-left:8px;">✓ Verified</span>'
    : '';
  const businessBadge = profile.is_business
    ? '<span class="badge badge-gold" style="margin-left:8px;">Business</span>'
    : '';

  container.innerHTML = `
    <img src="${profile.profile_pic_url}" alt="${profile.username}"
      style="width:80px;height:80px;border-radius:50%;object-fit:cover;border:2px solid rgba(255,77,0,0.3);">
    <div style="flex:1;min-width:200px;">
      <div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;">
        <h2 style="font-size:24px;font-weight:800;">@${profile.username}</h2>
        ${verifiedBadge}${businessBadge}
      </div>
      <p style="font-size:14px;color:rgba(245,245,245,0.5);margin-top:4px;">${profile.full_name}</p>
      <p style="font-size:13px;color:rgba(245,245,245,0.35);margin-top:8px;max-width:500px;line-height:1.5;">${profile.bio || 'No bio'}</p>
      ${profile.external_url ? `<a href="${profile.external_url}" target="_blank" style="font-size:12px;color:var(--blue-electric);margin-top:6px;display:inline-block;">${profile.external_url}</a>` : ''}
    </div>
    <div style="display:flex;gap:32px;flex-wrap:wrap;">
      <div style="text-align:center;">
        <div style="font-size:28px;font-weight:800;" class="glow-text">${formatNumber(profile.followers)}</div>
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.1em;color:rgba(245,245,245,0.4);">Followers</div>
      </div>
      <div style="text-align:center;">
        <div style="font-size:28px;font-weight:800;" class="glow-text">${formatNumber(profile.following)}</div>
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.1em;color:rgba(245,245,245,0.4);">Following</div>
      </div>
      <div style="text-align:center;">
        <div style="font-size:28px;font-weight:800;" class="glow-text">${formatNumber(profile.analyzed_posts)}</div>
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.1em;color:rgba(245,245,245,0.4);">Analyzed</div>
      </div>
    </div>
  `;
}

// ── Stats Grid ──
function renderStats(engagement, profile) {
  const container = document.getElementById('stats-grid');
  container.innerHTML = `
    <div class="stat-card section-animate stagger-1">
      <div class="stat-label">Engagement Rate</div>
      <div class="stat-value">${engagement.engagement_rate}%</div>
      <div class="stat-sub">${engagement.benchmark} · ${engagement.trend}</div>
    </div>
    <div class="stat-card section-animate stagger-2">
      <div class="stat-label">Avg Likes</div>
      <div class="stat-value">${formatNumber(engagement.avg_likes)}</div>
      <div class="stat-sub">per post</div>
    </div>
    <div class="stat-card section-animate stagger-3">
      <div class="stat-label">Avg Comments</div>
      <div class="stat-value">${formatNumber(engagement.avg_comments)}</div>
      <div class="stat-sub">per post</div>
    </div>
    <div class="stat-card section-animate stagger-4">
      <div class="stat-label">Follow Ratio</div>
      <div class="stat-value">${profile.follow_ratio}</div>
      <div class="stat-sub">followers / following</div>
    </div>
  `;
}

// ── Engagement Over Time Chart ──
function renderEngagementChart(engagement) {
  const ctx = document.getElementById('engagementChart').getContext('2d');

  const gradientLikes = ctx.createLinearGradient(0, 0, 0, 250);
  gradientLikes.addColorStop(0, 'rgba(255, 77, 0, 0.3)');
  gradientLikes.addColorStop(1, 'rgba(255, 77, 0, 0)');

  const gradientComments = ctx.createLinearGradient(0, 0, 0, 250);
  gradientComments.addColorStop(0, 'rgba(0, 93, 255, 0.3)');
  gradientComments.addColorStop(1, 'rgba(0, 93, 255, 0)');

  charts.engagement = new Chart(ctx, {
    type: 'line',
    data: {
      labels: engagement.dates,
      datasets: [
        {
          label: 'Likes',
          data: engagement.likes_over_time,
          borderColor: '#FF4D00',
          backgroundColor: gradientLikes,
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          pointHoverRadius: 6,
          pointBackgroundColor: '#FF4D00',
        },
        {
          label: 'Comments',
          data: engagement.comments_over_time,
          borderColor: '#005DFF',
          backgroundColor: gradientComments,
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          pointHoverRadius: 6,
          pointBackgroundColor: '#005DFF',
        },
      ],
    },
    options: chartOptions(),
  });
}

// ── Content Type Pie Chart ──
function renderContentChart(contentTypes) {
  const ctx = document.getElementById('contentChart').getContext('2d');
  const bd = contentTypes.breakdown;

  charts.content = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Images', 'Videos (Reels)', 'Carousels'],
      datasets: [{
        data: [bd.image.count, bd.video.count, bd.carousel.count],
        backgroundColor: ['#FF4D00', '#005DFF', '#FF8A00'],
        borderColor: ['#FF4D00', '#005DFF', '#FF8A00'],
        borderWidth: 0,
        hoverOffset: 8,
      }],
    },
    options: {
      ...chartOptions(),
      cutout: '65%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: 'rgba(245,245,245,0.5)',
            font: { size: 11, family: 'Inter' },
            padding: 16,
            usePointStyle: true,
            pointStyle: 'circle',
          },
        },
      },
    },
  });
}

// ── Day of Week Chart ──
function renderDayChart(patterns) {
  const ctx = document.getElementById('dayChart').getContext('2d');
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const values = days.map(d => patterns.day_engagement[d] || 0);
  const maxVal = Math.max(...values, 1);

  charts.day = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: days,
      datasets: [{
        label: 'Avg Engagement',
        data: values,
        backgroundColor: days.map(d =>
          d === patterns.best_day ? '#FF4D00' : 'rgba(255,255,255,0.06)'
        ),
        borderColor: days.map(d =>
          d === patterns.best_day ? '#FF4D00' : 'transparent'
        ),
        borderWidth: 1,
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      ...chartOptions(),
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: 'rgba(245,245,245,0.4)', font: { size: 11 } },
        },
        y: {
          display: false,
          grid: { display: false },
        },
      },
      plugins: { legend: { display: false } },
    },
  });
}

// ── Hour Chart ──
function renderHourChart(patterns) {
  const ctx = document.getElementById('hourChart').getContext('2d');
  const hours = Object.keys(patterns.hour_engagement);
  const values = Object.values(patterns.hour_engagement);
  const bestHour = patterns.best_hour;

  charts.hour = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: hours.filter((_, i) => i % 2 === 0),  // every 2 hours
      datasets: [{
        label: 'Avg Engagement',
        data: values.filter((_, i) => i % 2 === 0),
        backgroundColor: hours.filter((_, i) => i % 2 === 0).map(h =>
          h === bestHour ? '#005DFF' : 'rgba(255,255,255,0.06)'
        ),
        borderRadius: 4,
        borderSkipped: false,
      }],
    },
    options: {
      ...chartOptions(),
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: 'rgba(245,245,245,0.4)', font: { size: 10 } },
        },
        y: {
          display: false,
          grid: { display: false },
        },
      },
      plugins: { legend: { display: false } },
    },
  });
}

// ── Hashtags ──
function renderHashtags(hashtags) {
  // Cloud
  const cloudContainer = document.getElementById('hashtag-cloud');
  const maxCount = Math.max(...hashtags.hashtag_cloud.map(h => h.count), 1);
  cloudContainer.innerHTML = hashtags.hashtag_cloud.map(h => {
    const size = 11 + (h.count / maxCount) * 8;
    return `<span class="hashtag-tag" style="font-size:${size}px;">${h.text}</span>`;
  }).join('');

  // Best performing
  const bestContainer = document.getElementById('best-hashtags');
  bestContainer.innerHTML = hashtags.best_performing.map(([tag, eng]) => `
    <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);">
      <span style="font-size:13px;font-weight:600;color:var(--orange-gold);">${tag}</span>
      <span style="font-size:12px;color:rgba(245,245,245,0.4);">${formatNumber(eng)} avg eng.</span>
    </div>
  `).join('') || '<p style="font-size:13px;color:rgba(245,245,245,0.3);">Not enough hashtag data</p>';
}

// ── Caption Analysis ──
function renderCaptionAnalysis(caption) {
  const container = document.getElementById('caption-analysis');

  const toneColors = {
    'Professional': 'badge-blue',
    'Inspirational': 'badge-gold',
    'Casual': 'badge-orange',
    'Educational': 'badge-blue',
    'Promotional': 'badge-red',
    'Neutral': 'badge-orange',
  };

  container.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">
      <div style="padding:12px;background:rgba(255,255,255,0.03);border-radius:10px;text-align:center;">
        <div style="font-size:24px;font-weight:800;" class="glow-text">${caption.avg_length}</div>
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.1em;color:rgba(245,245,245,0.4);">Avg Chars</div>
      </div>
      <div style="padding:12px;background:rgba(255,255,255,0.03);border-radius:10px;text-align:center;">
        <div style="font-size:14px;font-weight:700;margin-top:4px;">
          <span class="badge ${toneColors[caption.dominant_tone] || 'badge-orange'}">${caption.dominant_tone}</span>
        </div>
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.1em;color:rgba(245,245,245,0.4);margin-top:4px;">Dominant Tone</div>
      </div>
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:6px;">
      ${Object.entries(caption.tone_scores).map(([tone, score]) =>
        score > 0 ? `<span class="badge ${toneColors[tone] || 'badge-orange'}" style="font-size:10px;">${tone}: ${score}</span>` : ''
      ).join('')}
    </div>
  `;

  // Common words
  const wordsContainer = document.getElementById('common-words');
  const maxWordCount = Math.max(...caption.common_words.map(w => w[1]), 1);
  wordsContainer.innerHTML = caption.common_words.map(([word, count]) => {
    const opacity = 0.4 + (count / maxWordCount) * 0.6;
    return `<span class="hashtag-tag" style="opacity:${opacity};">${word} <span style="color:rgba(245,245,245,0.3);">(${count})</span></span>`;
  }).join('');
}

// ── Top & Bottom Posts ──
function renderTopBottomPosts(posts) {
  const renderPost = (post, i) => `
    <div style="padding:12px 0;border-bottom:1px solid rgba(255,255,255,0.04);display:flex;gap:12px;align-items:flex-start;">
      <div style="font-size:20px;font-weight:800;color:rgba(245,245,245,0.15);min-width:24px;">${i + 1}</div>
      <div style="flex:1;">
        <div style="display:flex;gap:8px;align-items:center;margin-bottom:4px;">
          <span class="badge ${post.media_type === 'video' ? 'badge-blue' : post.media_type === 'carousel' ? 'badge-gold' : 'badge-orange'}" style="font-size:9px;">${post.media_type}</span>
          <span style="font-size:11px;color:rgba(245,245,245,0.3);">${post.date}</span>
        </div>
        <p style="font-size:12px;color:rgba(245,245,245,0.5);line-height:1.4;">${post.caption_preview || 'No caption'}</p>
        <div style="display:flex;gap:16px;margin-top:6px;">
          <span style="font-size:12px;color:var(--orange-flame);font-weight:600;">❤ ${formatNumber(post.likes)}</span>
          <span style="font-size:12px;color:var(--blue-electric);font-weight:600;">💬 ${formatNumber(post.comments)}</span>
        </div>
      </div>
      <a href="${post.url}" target="_blank" style="font-size:11px;color:rgba(245,245,245,0.3);white-space:nowrap;margin-top:4px;">View →</a>
    </div>
  `;

  document.getElementById('top-posts').innerHTML = posts.top_5.map(renderPost).join('');
  document.getElementById('bottom-posts').innerHTML = posts.bottom_5.map(renderPost).join('');
}

// ── Recommendations ──
function renderRecommendations(recs) {
  const container = document.getElementById('recommendations');
  const icons = {
    warning: '⚠️',
    opportunity: '🚀',
    tip: '💡',
    info: 'ℹ️',
  };

  container.innerHTML = recs.map(rec => `
    <div class="rec-card ${rec.type}">
      <div class="rec-title">${icons[rec.type] || '💡'} ${rec.title}</div>
      <div class="rec-text">${rec.text}</div>
    </div>
  `).join('');
}

// ── Posting Summary ──
function renderPostingSummary(patterns) {
  const container = document.getElementById('posting-summary');

  const items = [
    { label: 'Frequency', value: patterns.frequency, icon: '📅' },
    { label: 'Best Day', value: patterns.best_day, icon: '📆' },
    { label: 'Best Hour', value: patterns.best_hour, icon: '⏰' },
    { label: 'Avg Gap', value: `${patterns.avg_gap_days} days`, icon: '📊' },
  ];

  container.innerHTML = items.map(item => `
    <div style="padding:16px;background:rgba(255,255,255,0.02);border-radius:12px;text-align:center;border:1px solid rgba(255,255,255,0.04);">
      <div style="font-size:20px;margin-bottom:8px;">${item.icon}</div>
      <div style="font-size:18px;font-weight:800;" class="glow-text">${item.value}</div>
      <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.1em;color:rgba(245,245,245,0.4);margin-top:4px;">${item.label}</div>
    </div>
  `).join('');

  // Consistency bar
  const score = patterns.consistency_score;
  let scoreColor = '#D50032';
  if (score >= 70) scoreColor = '#FF8A00';
  if (score >= 85) scoreColor = '#005DFF';

  container.innerHTML += `
    <div style="padding:16px;background:rgba(255,255,255,0.02);border-radius:12px;border:1px solid rgba(255,255,255,0.04);grid-column:1/-1;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <span style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:rgba(245,245,245,0.5);">Consistency Score</span>
        <span style="font-size:20px;font-weight:800;color:${scoreColor};">${score}/100</span>
      </div>
      <div class="progress-bar">
        <div class="fill" style="width:${score}%;background:${score === patterns.consistency_score ? 'var(--gradient-fire)' : scoreColor};"></div>
      </div>
    </div>
  `;
}

// ── Chart Options ──
function chartOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      intersect: false,
      mode: 'index',
    },
    plugins: {
      legend: {
        display: true,
        position: 'top',
        align: 'end',
        labels: {
          color: 'rgba(245,245,245,0.5)',
          font: { size: 11, family: 'Inter', weight: '600' },
          padding: 16,
          usePointStyle: true,
          pointStyle: 'circle',
        },
      },
      tooltip: {
        backgroundColor: 'rgba(27,23,28,0.95)',
        titleColor: '#F5F5F5',
        bodyColor: 'rgba(245,245,245,0.7)',
        borderColor: 'rgba(255,255,255,0.08)',
        borderWidth: 1,
        cornerRadius: 10,
        padding: 12,
        titleFont: { size: 13, weight: '700', family: 'Inter' },
        bodyFont: { size: 12, family: 'Inter' },
        displayColors: true,
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(255,255,255,0.03)' },
        ticks: { color: 'rgba(245,245,245,0.35)', font: { size: 10, family: 'Inter' } },
      },
      y: {
        grid: { color: 'rgba(255,255,255,0.03)' },
        ticks: { color: 'rgba(245,245,245,0.35)', font: { size: 10, family: 'Inter' } },
      },
    },
  };
}

// ── Toast Notification ──
function showToast(message) {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100px)';
    toast.style.transition = 'all 0.4s';
    setTimeout(() => toast.remove(), 400);
  }, 4000);
}

// ── Number Formatter ──
function formatNumber(num) {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return Math.round(num).toString();
}
