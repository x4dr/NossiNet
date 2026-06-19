(function () {
    if (document.getElementById('nossi-tooltip-style')) return

    var container = document.getElementById('tooltip-container')
    if (!container) {
        container = document.createElement('div')
        container.id = 'tooltip-container'
        container.style.cssText = 'position:fixed;top:0;left:0;width:0;height:0;z-index:10000;'
    }

    function ensureContainer() {
        if (!container.parentNode && document.body) {
            document.body.appendChild(container)
        }
    }
    ensureContainer()
    if (!container.parentNode) {
        document.addEventListener('DOMContentLoaded', ensureContainer)
    }

    var cache = new Map()
    var hideTimer = null
    var activeTip = null

    function hide() {
        if (activeTip) {
            activeTip.classList.add('tip-fadeout')
            activeTip.style.opacity = '0'
            var el = activeTip
            setTimeout(function () {
                el.style.display = 'none'
                el.classList.remove('tip-fadeout')
            }, 300)
            activeTip = null
        }
    }

    function scheduleHide() {
        if (hideTimer) clearTimeout(hideTimer)
        hideTimer = setTimeout(hide, 200)
    }

    function cancelHide() {
        if (hideTimer) {
            clearTimeout(hideTimer)
            hideTimer = null
        }
    }

    function position(el, trigger) {
        var tr = trigger.getBoundingClientRect()
        var viewW = window.innerWidth
        var viewH = window.innerHeight

        var top = tr.bottom + 6
        var left = tr.left + tr.width / 2

        el.style.display = 'block'
        el.style.position = 'fixed'
        el.style.left = '0px'
        el.style.top = '0px'

        var ew = el.offsetWidth
        var eh = el.offsetHeight

        left = Math.min(left - ew / 2, viewW - ew - 8)
        left = Math.max(left, 8)

        if (top + eh > viewH - 8) {
            top = tr.top - eh - 6
        }
        if (top < 8) {
            top = 8
        }

        el.style.left = left + 'px'
        el.style.top = top + 'px'
    }

    function showTip(el, trigger) {
        cancelHide()
        if (activeTip && activeTip !== el) {
            activeTip.style.opacity = '0'
            activeTip.style.display = 'none'
        }
        el.classList.remove('tip-fadeout')
        el.style.opacity = '0'
        el.style.display = 'block'
        position(el, trigger)
        void el.offsetHeight
        el.style.opacity = '1'
        activeTip = el
    }

    function getTipContent(tipId) {
        return document.getElementById('tip-' + tipId)
    }

    function fetchTooltip(locator, trigger) {
        if (cache.has(locator)) {
            var cached = cache.get(locator)
            showTip(cached, trigger)
            return
        }

        var loading = document.createElement('div')
        loading.className = 'tip-content'
        loading.textContent = 'Loading...'
        loading.style.display = 'none'
        ensureContainer()
        container.appendChild(loading)
        cache.set(locator, loading)
        showTip(loading, trigger)

        var xhr = new XMLHttpRequest()
        xhr.open('GET', '/render/' + encodeURIComponent(locator), true)
        xhr.onload = function () {
            if (xhr.status === 200) {
                var div = document.createElement('div')
                div.className = 'tip-content'
                div.innerHTML = xhr.responseText
                ensureContainer()
                container.appendChild(div)
                cache.set(locator, div)
                if (loading.parentNode) loading.parentNode.removeChild(loading)
                if (activeTip === loading) {
                    showTip(div, trigger)
                }
            } else {
                loading.textContent = 'Not found'
            }
        }
        xhr.onerror = function () {
            loading.textContent = 'Error loading'
        }
        xhr.send()
    }

    document.addEventListener('mouseover', function (e) {
        var trigger = e.target.closest('[data-tip], [data-tooltip]')
        if (!trigger) return

        var tipId = trigger.getAttribute('data-tip')
        var locator = trigger.getAttribute('data-tooltip')

        if (tipId) {
            var content = getTipContent(tipId)
            if (content) {
                showTip(content, trigger)
            } else {
                fetchTooltip(tipId, trigger)
            }
        } else if (locator) {
            fetchTooltip(locator, trigger)
        }
    })

    document.addEventListener('mouseout', function (e) {
        var trigger = e.target.closest('[data-tip], [data-tooltip]')
        if (!trigger) return
        var related = e.relatedTarget
        if (related && related.closest && related.closest('.tip-content')) return
        if (related && related.closest && related.closest('[data-tip], [data-tooltip]')) return
        scheduleHide()
    })

    document.addEventListener('wheel', function (e) {
        var tip = e.target.closest('.tip-content')
        if (!tip) return
        var atTop = tip.scrollTop === 0
        var atBottom = tip.scrollHeight - tip.scrollTop - tip.clientHeight <= 1
        if ((e.deltaY < 0 && atTop) || (e.deltaY > 0 && atBottom)) {
            e.preventDefault()
        }
    }, { passive: false })

    document.addEventListener('mouseover', function (e) {
        var tip = e.target.closest('.tip-content')
        if (tip) cancelHide()
    })

    document.addEventListener('mouseout', function (e) {
        var tip = e.target.closest('.tip-content')
        if (!tip) return
        var related = e.relatedTarget
        if (related && related.closest && related.closest('.tip-content')) return
        if (related && related.closest && related.closest('[data-tip], [data-tooltip]')) return
        scheduleHide()
    })
})()
