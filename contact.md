---
layout: default
title: "お問い合わせ"
permalink: /contact/
---

## お問い合わせ

GadgetPostに関するお問い合わせは、以下のフォームよりお送りください。

<form action="https://formspree.io/f/placeholder" method="POST" class="contact-form">
  <div class="form-group">
    <label for="name">お名前</label>
    <input type="text" id="name" name="name" required>
  </div>

  <div class="form-group">
    <label for="email">メールアドレス</label>
    <input type="email" id="email" name="email" required>
  </div>

  <div class="form-group">
    <label for="subject">件名</label>
    <select id="subject" name="subject">
      <option value="general">一般的なお問い合わせ</option>
      <option value="content">記事内容に関するご指摘</option>
      <option value="ads">広告に関するお問い合わせ</option>
      <option value="other">その他</option>
    </select>
  </div>

  <div class="form-group">
    <label for="message">メッセージ</label>
    <textarea id="message" name="message" rows="6" required></textarea>
  </div>

  <button type="submit" class="submit-btn">送信する</button>
</form>

<p class="form-note">※ 通常2〜3営業日以内にご返信いたします。</p>
