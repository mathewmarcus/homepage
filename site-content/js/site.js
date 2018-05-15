function collapseNav(innerWidth) {
    var nav_collapse = document.getElementById("nav-collapse");
    if (innerWidth.matches) {
        nav_collapse.style.height = "0px";
    }
}

function toggleNav() {
    var nav_collapse = document.getElementById("nav-collapse");

    if (nav_collapse.style.height === "0px") {
        nav_collapse.style.height = nav_collapse.scrollHeight + 'px';
    }
    else {
        nav_collapse.style.height = "0px";
    }
}

hljs.initHighlightingOnLoad();
document.getElementById("nav-collapse").style.height = "0px";
window.matchMedia("(min-width: 600px)").addListener(collapseNav)
