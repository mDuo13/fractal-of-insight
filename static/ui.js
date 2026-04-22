function toggle(q) {
    const togtarget = document.querySelectorAll(q)
    togtarget.forEach(el => {el.classList.toggle("collapse") })
    const anchor = q.match(/#[a-z_\-]+/)
    if (anchor && anchor[0]) {
        history.replaceState("", document.title, window.location.pathname+anchor)
    }
}
function show(q) {
    const els = document.querySelectorAll(q)
    els.forEach(el => {el.classList.remove("collapse")})
}
function hide(q) {
    const els = document.querySelectorAll(q)
    els.forEach(el => {el.classList.add("collapse")})
}
function settitle(q) {
    try {
        const title = document.querySelector(q).querySelector("h3").innerText
        document.og_title = document.title
        document.title = `${title} - ${document.og_title}`
    } catch(e) {console.debug(`not setting title for ${q}; probably no h3 (err: ${e})`)}
}
function unsettitle() {
    if (document.og_title) {
        document.title = document.og_title
    }
}
function opendecklist(q) {
    hide(".decklist")
    show(q)
    settitle(q)
    window.location.replace(window.location.pathname+window.location.search+q)
}
function closedecklist(q) {
    hide(q)
    unsettitle()
    history.replaceState(null, "", window.location.pathname+window.location.search)
}
function togglegfx() {
    toggle(".deck_gfx")
    toggle(".deck_txt")
}
function showteammatches(tslug) {
    hide("#matches .match") // hide all
    show(`#matches .t_${tslug}`) // show matching

    show("#matches > .togglable")
    show("#matchreset")
    show("#keymatch-expl")
    hide("#keymatch-showing")
    window.location.hash = "#matches"
}
function show_wins() {
    hide("#sightings tbody tr")
    show("#sightings .winner")
    show("#sightings > .togglable")
    show("#sightingsreset")
    show("#wins-expl")
    hide("#wins-filter")
    hide(".event-filters")
    window.location.hash = "#sightings"
}
function reset_sightings() {
    show("#sightings tr")
    hide("#sightingsreset")
    hide("#wins-expl")
    show("#wins-filter")
    show(".event-filters")
    update_evt_filtering()
}
// match filtering
function showmatches(pid) {
    // show all matches with a given player
    hide("#matches .match")
    show(`#matches .p_${pid}`)

    show("#matches > .togglable")
    show("#matchreset")
    hide("#keymatch-expl")
    hide("#keymatch-showing")
    hide("#keymatches")
    window.location.hash = "#matches"
}
function show_matchup_matches(arche1, arche2) {
    // show all matches between two archetypes
    // (Note: it's structured as p1/p2 instead of generally a list of
    // archetypes is because some decks can be multi-archetypes and I
    // don't want a search for, for example, Water Allies vs Crux to
    // return for example a Water Crux Allies vs [some rando] match.)
    hide("#matches .match")
    show(`[data-p1-archetypes*="${arche1}"][data-p2-archetypes*="${arche2}"]`)
    show(`[data-p1-archetypes*="${arche2}"][data-p2-archetypes*="${arche1}"]`)

    show("#matches > .togglable")
    show("#matchreset")
    hide("#keymatch-expl")
    hide("#keymatch-showing")
    hide("#keymatches")
}
function show_arche_matches(arche1) {
    // show all matches involving an archetype
    hide("#matches .match")
    show(`[data-p1-archetypes*="${arche1}"]`)
    show(`[data-p2-archetypes*="${arche1}"]`)

    show("#matches > .togglable")
    show("#matchreset")
    hide("#keymatch-expl")
    hide("#keymatch-showing")
    hide("#keymatches")
}
function show_key_matches() {
    hide("#keymatches")
    show("#matchreset")

    // Switch the labels
    hide("#keymatch-expl")
    show("#keymatch-showing")

    hide("#matches .match")
    show("#matches > .togglable")
    show("#matches .keymatch")
}
function show_vid_matches() {
    hide("#showvids")
    show("#matchreset")

    hide("#matches .match")
    show("#matches > .togglable")
    show("#matches .hasvideo")
}
function reset_matches() {
    hide("#matchreset")
    show("#keymatches")
    show("#matches .match")
    show("#showvids")

    // Switch the labels
    show("#keymatch-expl")
    hide("#keymatch-showing")
}

function opentab(tabbutton, selector) {
    const tabbuttons = tabbutton.parentElement.querySelectorAll(".tab")
    tabbuttons.forEach(el => {el.classList.remove("activetab")})
    tabbutton.classList.add("activetab")

    if (selector === undefined) {
        const tabfor = tabbutton.dataset.tabfor
        selector = `[data-tabof="${tabfor}"]`
    }

    const tabparent = tabbutton.parentElement.parentElement
    const target_tab = tabparent.querySelector(selector)
    // Only sibling tabs and not tabs of other groups in the same area
    const tabs = target_tab.parentElement.querySelectorAll(".tabcontent")
    for (const tab of tabs) {
        if (tab === target_tab) {
            tab.classList.remove("collapse")
        } else {
            tab.classList.add("collapse")
        }
    }
}

function opentabs(tabbutton) {
    const tabfor = tabbutton.dataset.tabfor
    const tabbuttons = document.querySelectorAll(".tab")
    const matchingtabs = document.querySelectorAll(`[data-tabfor="${tabfor}"]`)
    tabbuttons.forEach(el => {el.classList.remove("activetab")})
    matchingtabs.forEach(el => {el.classList.add("activetab")})

    const alltabcontent = document.querySelectorAll(".tabcontent")
    const matchingtabcontent = document.querySelectorAll(`[data-tabof="${tabfor}"]`)
    alltabcontent.forEach(el => {el.classList.add("collapse")})
    matchingtabcontent.forEach(el => {el.classList.remove("collapse")})
}

function update_evt_filtering() {
    const decklist_cb = document.getElementById("cb_decklists")
    let decklists_only = false
    if (decklist_cb) {
        decklists_only = decklist_cb.checked
    }
    const small_evts_cb = document.getElementById("cb_small_events")
    let small_events = false
    if (small_evts_cb) {
        small_events = small_evts_cb.checked
    }
    const st_radios = document.getElementsByName("subtype")
    let checked_subtype = ""
    if (st_radios.length) {
        for (el of st_radios) {
            if (el.checked) {
                if (el.value === "(All)") {
                    // Leave checked_subtype as empty
                    break
                }
                checked_subtype = el.value
                break
            }
        }
    }

    const show_cats = []
    document.querySelectorAll('input[name="category"]').forEach( el => {
        if (el.checked) {
            show_cats.push(el.value)
        }
    })

    // Filter events (e.g. on homepage, season page)
    document.querySelectorAll('.evt').forEach( el => {
        if (decklists_only && el.dataset["decklists"] == "0") {
            el.classList.add("collapse")
        } else if (!small_events && parseInt(el.dataset["playercount"]) < 20
                    && el.dataset["category"] !== "worlds") {
                    // Special case: show Worlds (2024) even though it's "small"
            el.classList.add("collapse")
        } else {
            if ( show_cats.includes(el.dataset["category"]) ) {
                el.classList.remove("collapse")
            } else {
                el.classList.add("collapse")
            }
        }
    })

    // Filter rows (e.g. on archetype page)
    document.querySelectorAll('.p-row').forEach( el => {
        let el_sts = []
        if (el.dataset.hasOwnProperty("subtypes")) {
            el_sts = JSON.parse(el.dataset["subtypes"])
        }

        if (decklists_only && el.dataset["decklists"] == "0") {
            el.classList.add("collapse")
        } else if (!small_events && parseInt(el.dataset["playercount"]) < 20) {
            el.classList.add("collapse")
        } else {
            if ( show_cats.includes(el.dataset["category"]) &&
                 ( !checked_subtype || el_sts.includes(checked_subtype) ) ) {
                el.classList.remove("collapse")
            } else {
                el.classList.add("collapse")
            }
        }
    })
}

function copypermalink() {
    if (window.isSecureContext) {
        navigator.clipboard.writeText(window.location)
    }
}

function omnidexexport(q) {
    if (window.isSecureContext) {
        const textarea = document.querySelector(q)
        navigator.clipboard.writeText(textarea.textContent)
    }
}

function carddetail(c) {
    c.classList.toggle("dblclicked")
    c.querySelector(".carddeets").classList.toggle("collapse")
}
function flipcard(event, c) {
    event.stopPropagation()
    c.querySelector(".cardfront").classList.toggle("flipped")
    c.querySelector(".cardback").classList.toggle("flipped")
}

function ready(callback) {
  if (document.readyState != "loading") callback()
  else document.addEventListener("DOMContentLoaded", callback)
}

function search_table(el) {
    const searchbox = el.parentElement.querySelector(".searchbox")
    const search_query = searchbox.value
    const trs = document.querySelectorAll(searchbox.dataset["target"])

    for (const tr of trs) {
        if(tr.textContent.toLowerCase().includes(search_query.toLowerCase())) {
            tr.classList.remove("collapse")
        } else {
            tr.classList.add("collapse")
        }
    }
}

function reset_search(el) {
    const searchbox = el.parentElement.querySelector(".searchbox")
    searchbox.value = ""
    const trs = document.querySelectorAll(el.dataset["target"])
    for (const tr of trs) {
        tr.classList.remove("collapse")
    }
    searchbox.focus()
}

async function populate_avatar(el) {
    const pid = el.dataset["pid"]
    const avatardata = await (await fetch(`https://accounts.gatcg.com/user/avatar?userId=${pid}`)).json()
    el.innerHTML = `
    <img src="https://accounts.gatcg.com${avatardata.image}" 
        alt="" class="avatar-image" />
    <img src="https://accounts.gatcg.com${avatardata.frame}" 
        alt="" class="avatar-frame" />
    `
}

let CARDDATA
async function load_carddata() {
    try {
        CARDDATA = await (await fetch("/card/carddata.json")).json()
    } catch (err) {
        console.error("Error loading data files. Price/frequency information may not load correctly.", err)
    }
}

function str_thirds(num) {
    // Assuming a float that's in increments of ⅓ (possibly imprecise)
    // return a string in fraction form
    if (parseInt(num) == num) {
        return num.toString()
    }
    let intstr = ''
    if (parseInt(num) != 0) {
        intstr = parseInt(num).toString()
    }
    if (num % 1 < 0.5) {
        return intstr+'⅓'
    }
    return intstr+'⅔'
}

async function calc_trailblazer() {
    if (!CARDDATA) { await load_carddata() }

    const textbox = document.querySelector("#trailblazer-dl")
    const deetbox = document.querySelector("#trailblazer-detail")
    deetbox.innerHTML = ""
    const COMMENT_REGEX = /# (?<comment>.*)$/
    const CARD_REGEX = /(?<quantity>[0-9]+) (?<card>.*)$/
    let dl_txt = textbox.value
    let tb_total = 0
    let is_sideboard = false
    let no_points = []
    for (line of dl_txt.split("\n")) {
        const cm = line.match(COMMENT_REGEX)
        if (cm && cm.groups.comment) {
            const comment = cm.groups.comment.trim().toLowerCase()
            if (comment == "sideboard" || comment == "side") {
                is_sideboard = true
            } else if (comment in ['main','main deck','maindeck','material','material deck']) {
                is_sideboard = false
            } else {
                // random comment, no-op
            }
        } else if (line.trim()) {
            const m = line.match(CARD_REGEX)
            if (m && m.groups.card) {
                const cardname = m.groups.card.trim()
                if (cardname in CARDDATA) {
                    const appearances = CARDDATA[cardname].a
                    // material deck cards score triple points
                    const mat_mult = CARDDATA[cardname].mat ? 3 : 1
                    const quant = parseInt(m.groups.quantity)
                    const sb_mult = is_sideboard ? (1.0/3) : 1
                    if (appearances <= 10) {
                        const pts = quant * mat_mult * 2 * sb_mult
                        tb_total += pts
                        if (is_sideboard) { deetbox.innerText += '(Sideboard) ' }
                        deetbox.innerText += `${quant} ${cardname}: ${str_thirds(pts)} points (${appearances} appearances)\n`
                    } else if (appearances <= 100) {
                        const pts = quant * mat_mult * sb_mult
                        tb_total += pts
                        if (is_sideboard) { deetbox.innerText += '(Sideboard) ' }
                        deetbox.innerText += `${quant} ${cardname}: ${str_thirds(pts)} points (${appearances} appearances)\n`
                    } else {
                        no_points.push(cardname)
                    }
                } else {
                    console.error("Couldn't find card data for:", m.groups.card)
                }
            } else {
                console.error("Unknown line in decklist:", line)
            }
        } // else blank line
    }

    const resultfield = document.querySelector("#trailblazer-result")
    resultfield.innerText = str_thirds(tb_total)
    deetbox.innerText += '\nNot worth trailblazer points: ' + no_points.join('; ')
}

function make_tables_sortable() {
    // Adapted from - https://stackoverflow.com/a/49041392
    // Posted by Nick Grealy, modified by community.
    // Retrieved 2026-03-02, License - CC BY-SA 4.0
    const sortable_ths = document.querySelectorAll('.sortable th')
    const getCellValue = (tr, idx) => {
        const text = tr.children[idx].innerText || tr.children[idx].textContent
        if (text && text.slice(0,1) == "$") {
            return text.slice(1)
        }
        if (text && text.slice(-1) == "%") {
            return text.slice(0,-1)
        }
        if (text && text.trim() == "N/A (Proxia's Vault)") return "0"
        return text
    }
    const comparer = (idx, asc) => (a, b) => ((v1, v2) => 
        v1 !== '' && v2 !== '' && !isNaN(v1) && !isNaN(v2) ? v1 - v2 : v1.toString().localeCompare(v2)
        )(getCellValue(asc ? a : b, idx), getCellValue(asc ? b : a, idx));
    
    for (const th of sortable_ths) {
        th.addEventListener('click', (() => {
            const table = th.closest('table')
            Array.from(table.querySelectorAll('tbody tr'))
                .sort(comparer(Array.from(th.parentNode.children).indexOf(th), this.asc = !this.asc))
                .forEach(tr => table.tBodies[0].appendChild(tr) );
        }))
    }
}

function show_previous_deck(btn) {
    const thisdeck = btn.closest(".decklist")
    const newdeck = thisdeck.previousElementSibling
    if (!newdeck || !newdeck.classList.contains("decklist")) {
        return false
    }
    unsettitle()
    opendecklist(`#${newdeck.id}`)
}
function show_next_deck(btn) {
    const thisdeck = btn.closest(".decklist")
    const newdeck = thisdeck.nextElementSibling
    if (!newdeck || !newdeck.classList.contains("decklist")) {
        return false
    }
    unsettitle()
    opendecklist(`#${newdeck.id}`)
}

function close_all(event) {
    if (event.key === "Escape") {
        closedecklist(".decklist")
    }
}

function h_scrollable(el) {
    el.addEventListener("pointerdown", (evt) => {
        evt.preventDefault()
        el.setPointerCapture(evt.pointerId)
    })
    el.addEventListener("pointerup", (evt) => {
        evt.preventDefault()
        el.setPointerCapture(evt.pointerId)
    })
    el.addEventListener("pointermove", (evt) => {
        if (el.hasPointerCapture(evt.pointerId) && evt.isPrimary) {
            el.scrollLeft -= evt.movementX
            evt.preventDefault()
        }
    })
}

ready(() => {
    // Open hash on page-load
    if (window.location.hash) {
        //console.debug("hash:",window.location.hash)
        const defaultobj = document.querySelector(window.location.hash)
        if (defaultobj && defaultobj.classList.contains("collapse")) {
            defaultobj.classList.remove("collapse")
            settitle(window.location.hash)
        } else {
            q = `${window.location.hash} > .togglable.collapse`
            //collapsedChildren = document.querySelectorAll(q)
            show(q)
        }
    }

    // Re-apply event filters
    if (document.querySelector(".event-filtering")) {
        update_evt_filtering()
    }

    // Attach decklist closing events
    document.querySelectorAll(".decklist").forEach(el => {
        el.addEventListener("click", (evt) => {
            if (evt.target.href) {
                // is a link, do the default after closing this
                el.classList.add("collapse")
            }
            else if (!evt.target.classList.contains("decklist")) {
                evt.preventDefault()
            } else {
                el.classList.add("collapse")
                history.replaceState(null, "", window.location.pathname+window.location.search)
                if (document.og_title) {
                    document.title = document.og_title
                }
            }
        })
    })

    // Set up find-as-you-type delay (if needed)
    let typingTimer
    const typeInterval = 200
    const searchbox = document.querySelector(".searchbox")
    if (searchbox) {
        searchbox.addEventListener('keyup', (event) => {
            clearTimeout(typingTimer)
            typingTimer = setTimeout(() => {search_table(event.target)}, typeInterval)
        })
    }

    document.querySelectorAll(".player-omni-avatar").forEach(populate_avatar)
    make_tables_sortable()

    document.querySelectorAll(".gallery").forEach(h_scrollable)

    document.addEventListener('keydown', close_all)
})

