---
layout: default
title: "セール・キャンペーン情報"
description: "Amazon・楽天の最新セール情報とおすすめガジェットをジャンル別にまとめています。通常価格との比較で本当にお得な商品だけを厳選。"
---

<section class="sale-hub">
  <h1 class="sale-hub-title">セール・キャンペーン情報</h1>
  <p class="sale-hub-desc">Amazon・楽天の最新セール情報をジャンル別に整理。通常価格と比較して本当にお得な商品だけを厳選してお届けします。</p>

  <div class="sale-event-grid">
    <a href="/sale/amazon-spring-2026/" class="sale-event-card sale-event-active">
      <span class="sale-event-badge">開催中</span>
      <h2>Amazon新生活セール 2026</h2>
      <p class="sale-event-period">2026年3月28日〜4月2日</p>
      <p class="sale-event-desc">新生活に必要なガジェットが最大50%OFF。Echo、Fire TV、Kindleなど定番商品が大幅値下げ。</p>
    </a>
    <a href="/sale/rakuten-marathon-202604/" class="sale-event-card">
      <span class="sale-event-badge sale-event-upcoming">まもなく</span>
      <h2>楽天お買い物マラソン 4月</h2>
      <p class="sale-event-period">2026年4月9日〜4月16日</p>
      <p class="sale-event-desc">ポイント最大46.5倍。Apple Watch、充電器、Wi-Fiルーターがお買い得。</p>
    </a>
  </div>

  <h2 class="section-title">ジャンル別おすすめ</h2>
  <div class="genre-grid">
    <a href="/sale/amazon-spring-2026/#audio" class="genre-card">
      <span class="genre-icon">🎧</span>
      <span class="genre-name">オーディオ</span>
      <span class="genre-count">AirPods Pro, Sony WF/WHなど</span>
    </a>
    <a href="/sale/amazon-spring-2026/#smart-device" class="genre-card">
      <span class="genre-icon">📱</span>
      <span class="genre-name">スマートデバイス</span>
      <span class="genre-count">Echo, Fire TV, Kindleなど</span>
    </a>
    <a href="/sale/amazon-spring-2026/#charger" class="genre-card">
      <span class="genre-icon">🔋</span>
      <span class="genre-name">充電器・バッテリー</span>
      <span class="genre-count">Anker, UGREENなど</span>
    </a>
    <a href="/sale/amazon-spring-2026/#tablet" class="genre-card">
      <span class="genre-icon">📋</span>
      <span class="genre-name">タブレット</span>
      <span class="genre-count">iPad Air, Galaxy Tabなど</span>
    </a>
  </div>

  <h2 class="section-title">セール記事一覧</h2>
  <ul class="post-list">
    {% for post in site.posts %}
      {% if post.tags contains "セール" or post.categories contains "セール" or post.slug contains "sale" %}
      <li class="post-list-item">
        {% if post.thumbnail %}
        <div class="card-thumbnail">
          <img src="{{ post.thumbnail }}" alt="{{ post.title }}" loading="lazy" onerror="this.style.display='none'">
        </div>
        {% endif %}
        <div class="card-body">
          <h3><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
          <div class="post-meta">
            <time>{{ post.date | date: "%Y年%-m月%-d日" }}</time>
            {% for cat in post.categories %}
              <span class="post-category"><a href="/category/{% include cat_slug.html name=cat %}/">{{ cat }}</a></span>
            {% endfor %}
          </div>
        </div>
      </li>
      {% endif %}
    {% endfor %}
  </ul>
</section>
