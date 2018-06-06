function collapseNav(innerWidth) {
    var nav_collapse = document.getElementById('nav-collapse');
    if (innerWidth.matches) {
        nav_collapse.style.height = '0px';
    }
}

function toggleNav() {
    var nav_collapse = document.getElementById('nav-collapse');

    if (nav_collapse.style.height === '0px') {
        nav_collapse.style.height = nav_collapse.scrollHeight + 'px';
    }
    else {
        nav_collapse.style.height = '0px';
    }
}

function add_email() {
    email_social_a = document.getElementsByClassName('social_email')
    for(var i = 0; i < email_social_a.length; i++) {
	email_social_a[i].setAttribute('href', 'mailto:' + 'mathewmarcus456' + '@' + 'gmail.com')
    }
}

hljs.initHighlightingOnLoad();
document.getElementById('nav-collapse').style.height = '0px';
window.matchMedia('(min-width: 600px)').addListener(collapseNav);
document.addEventListener('DOMContentLoaded', function() {
    document.addEventListener('mousemove', add_email, {once: true})
}, {once: true});

