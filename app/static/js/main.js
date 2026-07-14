(function() {
    window.showToast = function(msg, type) {
        type = type || 'info';
        var c = document.querySelector('.toast-container');
        if (!c) { c = document.createElement('div'); c.className = 'toast-container'; document.body.appendChild(c); }
        var t = document.createElement('div');
        t.className = 'toast ' + type;
        t.textContent = msg;
        c.appendChild(t);
        setTimeout(function() { t.classList.add('fade-out'); setTimeout(function() { t.remove(); }, 300); }, 3000);
    };

    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('.tz-local').forEach(function(el) {
            var dt = el.getAttribute('data-time');
            if (dt) { el.textContent = new Date(dt).toLocaleString(); }
        });
    });
})();
