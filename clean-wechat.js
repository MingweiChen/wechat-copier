// clean-wechat.js — 微信富文本复制前的 HTML 清洗（移植自 wechat-article-workflow/scripts/clean-html.py）
// 解决微信安卓 APP（X5 内核）把标签间空白/换行拆成大量空行空格的问题。
// 用于复制到剪贴板前压缩 HTML —— 剪贴板不需人读，做完全压缩对安卓最安全。
// 全局暴露 window.cleanWechatHtml(html) -> cleanedHtml
(function () {
  function cleanWechatHtml(html) {
    if (!html) return html;
    // 1. 删除 HTML 注释
    html = html.replace(/<!--[\s\S]*?-->/g, "");
    // 2. 多余换行/回车 → 单个 \n
    html = html.replace(/[\r\n]+/g, "\n");
    // 3. 删除标签之间的所有空白（完全压缩，安卓安全）
    html = html.replace(/>\s+</g, "><");
    // 4. 块级标签 div/h1-6/article/header/footer → p（与 clean-html.py 一致；
    //    本仓库 HTML 用 section/p/table，不含这些标签，等于 no-op，但保留以防万一）
    var BLOCK_TO_P = ["div", "h1", "h2", "h3", "h4", "h5", "h6", "article", "header", "footer"];
    BLOCK_TO_P.forEach(function (tag) {
      html = html.replace(new RegExp("<" + tag + "(\\s+[^>]*)?>", "gi"), function (_m, attrs) {
        return "<p" + (attrs || "") + ">";
      });
      html = html.replace(new RegExp("</" + tag + ">", "gi"), "</p>");
    });
    // 5. 删除空白 span
    html = html.replace(/<span[^>]*>\s*<\/span>/gi, "");
    // 6. 删除空白 p（连续空段落）
    html = html.replace(/<p[^>]*>\s*<\/p>/gi, "");
    // 7. 合并连续 &nbsp;（>2 → 1）
    html = html.replace(/(&nbsp;){2,}/g, "&nbsp;");
    // 8. 合并连续 <br>（>2 → 2）
    html = html.replace(/(<br\s*\/?>){3,}/gi, "<br><br>");
    // 9. 删除 <p> 开头的 <br>
    html = html.replace(/<p([^>]*)>\s*<br\s*\/?>/gi, "<p$1>");
    // 10. 删除 </p> 前的 <br>
    html = html.replace(/<br\s*\/?>\s*<\/p>/gi, "</p>");
    // 11. 删除 <p> 首尾普通空格
    html = html.replace(/<p([^>]*)>\s+/g, "<p$1>");
    html = html.replace(/\s+<\/p>/g, "</p>");
    // 12. style 属性值内空白压成单空格
    html = html.replace(/style="([^"]*)"/g, function (_m, s) {
      return 'style="' + s.replace(/\s+/g, " ").trim() + '"';
    });
    // 13. 删除空 style 属性
    html = html.replace(/\s*style="\s*"/g, "");
    return html.trim();
  }
  window.cleanWechatHtml = cleanWechatHtml;
})();
