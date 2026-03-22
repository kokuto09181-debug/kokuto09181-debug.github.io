---
layout: default
title: "セール・キャンペーン情報"
description: "Amazonの最新セール情報とおすすめガジェットをジャンル別にまとめています。過去の価格推移と比較して本当にお得な商品だけを厳選。"
---

<section class="sale-hub">
  <h1 class="sale-hub-title">セール・キャンペーン情報</h1>
  <p class="sale-hub-desc">Amazonの最新セール情報をジャンル別に整理。Keepaの価格追跡データを参考に、過去の最安値と比較して本当にお得な商品だけをお届けします。</p>

  <div class="sale-event-grid">
    <a href="/sale/amazon-spring-2026/" class="sale-event-card sale-event-active">
      <span class="sale-event-badge">開催予定</span>
      <h2>Amazon新生活セール 2026</h2>
      <p class="sale-event-period">2026年3月28日〜4月2日</p>
      <p class="sale-event-desc">新生活に必要なガジェットが最大63%OFF。AirPods Pro、Echo Dot、Fire TV Stick、Kindle Paperwhiteなど人気商品を過去価格と比較して紹介。</p>
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
      <span class="genre-count">Anker充電器など</span>
    </a>
    <a href="/sale/amazon-spring-2026/#tablet" class="genre-card">
      <span class="genre-icon">📋</span>
      <span class="genre-name">タブレット</span>
      <span class="genre-count">iPad Airなど</span>
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
