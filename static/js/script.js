// クリップボードにIDを保存
var clipboard = new ClipboardJS('.copy');
// クリップ成功
clipboard.on('success', (e) => {
    const title = e.trigger.dataset.clipboardTitle;
    alert(title + 'をコピーしたよ');
});