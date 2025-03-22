function toggle(q) {
    const togtarget = document.querySelectorAll(q)
    togtarget.forEach(el => {el.classList.toggle("collapse") })
}
function show(q) {
    const els = document.querySelectorAll(q)
    els.forEach(el => {el.classList.remove("collapse")})
}
function hide(q) {
    const els = document.querySelectorAll(q)
    els.forEach(el => {el.classList.add("collapse")})
}
function opendecklist(q) {
    show(q)
    window.location.replace(window.location.pathname+window.location.search+q)
}
function closedecklist(q) {
    hide(q)
    //window.location.replace(window.location.pathname+window.location.search)
    history.pushState("", document.title, window.location.pathname+window.location.search)
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
function reset_matches() {
    hide("#matchreset")
    show("#keymatches")
    show("#matches .match")

    // Switch the labels
    show("#keymatch-expl")
    hide("#keymatch-showing")
}
function opentab(tabbutton, selector) {
    const tabbuttons = tabbutton.parentElement.querySelectorAll(".tab")
    tabbuttons.forEach(el => {el.classList.remove("activetab")})
    tabbutton.classList.add("activetab")

    const tabcontent = document.querySelector(selector)
    const tabs = tabcontent.parentElement.querySelectorAll(".tabcontent")
    tabs.forEach(el => {el.classList.add("collapse")})
    tabcontent.classList.remove("collapse")
}

function update_evt_filtering() {
    const decklist_cb = document.getElementById("cb_decklists")
    let decklists_only = false
    if (decklist_cb) {
        decklists_only = decklist_cb.checked
    }
    const show_cats = []
    document.querySelectorAll('input[name="category"]').forEach( el => {
        if (el.checked) {
            show_cats.push(el.value)
        }
    })
    //console.log("show_cats", show_cats)
    document.querySelectorAll('.evt').forEach( el => {
        if (decklists_only && el.dataset["decklists"] == "0") {
            el.classList.add("collapse")
        } else {
            if ( show_cats.includes(el.dataset["category"]) ) {
                el.classList.remove("collapse")
            } else {
                el.classList.add("collapse")
            }
        }
    })
    document.querySelectorAll('.p-row').forEach( el => {
        if (decklists_only && el.dataset["decklists"] == "0") {
            el.classList.add("collapse")
        } else {
            if ( show_cats.includes(el.dataset["category"]) ) {
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
