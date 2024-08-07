function toggle(q) {
    const togtarget = document.querySelectorAll(q)
    togtarget.forEach(el => {el.classList.toggle("collapse") })
}
function opendecklist(q) {
    const deckoverlay = document.querySelector(q)
    deckoverlay.classList.remove("collapse")
    window.location.replace(window.location.pathname+window.location.search+q)
}
function closedecklist(q) {
    const deckoverlay = document.querySelector(q)
    deckoverlay.classList.add("collapse")
    //window.location.replace(window.location.pathname+window.location.search)
    history.pushState("", document.title, window.location.pathname+window.location.search)
}
function togglegfx() {
    const gfx = document.querySelectorAll(".deck_gfx")
    gfx.forEach(el => {el.classList.toggle("collapse")})
    const txt = document.querySelectorAll(".deck_txt")
    txt.forEach(el => {el.classList.toggle("collapse")})
}
function showmatches(pid) {
    const all_matches = document.querySelectorAll("#matches .match")
    all_matches.forEach(el => {el.classList.add("collapse")})
    const matching_matches = document.querySelectorAll(`#matches .p_${pid}`)
    matching_matches.forEach(el => {el.classList.remove("collapse")})
    const matchsection = document.querySelector("#matches > .togglable")
    matchsection.classList.remove("collapse")
    const matchreset = document.querySelector("#matchreset")
    matchreset.classList.remove("collapse")
    window.location.hash = "#matches"
}
function reset_matches() {
    const matchreset = document.querySelector("#matchreset")
    matchreset.classList.add("collapse")
    const all_matches = document.querySelectorAll("#matches .match")
    all_matches.forEach(el => {el.classList.remove("collapse")})
}

function update_evt_filtering() {
    const decklists_only = document.getElementById("cb_decklists").checked
    const show_cats = []
    document.querySelectorAll('input[name="category"]').forEach( el => {
        if (el.checked) {
            show_cats.push(el.value)
        }
    })
    console.log("show_cats", show_cats)
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
}
