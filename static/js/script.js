function copy() {
    var text = document.getElementById("copyTarget");
    text.select();
    document.execCommand("Copy");
}