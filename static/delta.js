function show_delta_error(msg) {
    const errmsg = document.querySelector("#delta-err")
    errmsg.innerText = msg
    errmsg.classList.remove("collapse")
}

function cmp_card_o(a,b) {
    // requires carddb to be loaded separately
    if (carddb[a["card"]].rank == carddb[b["card"]].rank) {
        return 0
    } else if (carddb[a["card"]].rank > carddb[b["card"]].rank) {
        return 1
    }
    return -1
}

function normalize_dl(dlw) {
    if (!dlw || !dlw.decklist) { return }
    for (const card_o of dlw.decklist.material) {
        card_o["card"] = card_o["card"].toLowerCase()
    }
    for (const card_o of dlw.decklist.main) {
        card_o["card"] = card_o["card"].toLowerCase()
    }
    for (const card_o of dlw.decklist.sideboard) {
        card_o["card"] = card_o["card"].toLowerCase()
    }
    dlw.decklist.material.sort(cmp_card_o)
    dlw.decklist.main.sort(cmp_card_o)
    dlw.decklist.sideboard.sort(cmp_card_o)
    return dlw.decklist
}

async function get_dls() {
    const evt1_id = document.querySelector("#delta-evt-1").value
    const evt2_id = document.querySelector("#delta-evt-2").value
    const p1_id = parseInt(document.querySelector("#delta-p-1").value)
    const p2_id = parseInt(document.querySelector("#delta-p-2").value)
    if (!evt1_id || !evt2_id || !p1_id || !p2_id) {
        show_delta_error("Must supply valid Omni IDs for both events and both players")
        return
    }
    // TODO: check numberliness of all four inputs?

    const e1_dls = await (await fetch(`https://api.gatcg.com/omnidex/events/${evt1_id}/decklists`)).json()
    let e2_dls
    if (evt1_id == evt2_id) {
        e2_dls = e1_dls
    } else {
        e2_dls = await (await fetch(`https://api.gatcg.com/omnidex/events/${evt2_id}/decklists`)).json()
    }

    const p1_dlw = e1_dls.find( (dlwrap) => dlwrap.player == p1_id )
    const p2_dlw = e2_dls.find( (dlwrap) => dlwrap.player == p2_id )
    // TODO: sort decklists (requires Index data for omni sort)
    return {"p1": normalize_dl(p1_dlw), "p2": normalize_dl(p2_dlw) }
}
function reset_results() {
    const dv = document.querySelector("#delta-view")
    let els = Array.from(dv.querySelectorAll(".name"))
    els = els.concat(Array.from(dv.querySelectorAll(".cardcount")))
    els = els.concat(Array.from(dv.querySelectorAll(".deck_gfx")))
    for (const el of els) {
        el.innerHTML = ""
    }
    const errmsg = document.querySelector("#delta-err")
    errmsg.innerHTML = ""
    errmsg.classList.add("collapse")
}

function cardimg(card_o) {
    // requires carddb
    const el = document.createElement("div")
    el.classList.add("cardimg")
    el.innerHTML = `
    <img src="${carddb[card_o.card].img}" alt="${card_o.card}" />
    <span class="quant">${card_o.quantity}</span>
    `
    if (card_o.quantity.slice(0,1) == "-") {
        el.classList.add("minus")
    }
    return el
}

function calc_delta(lista, listb) {
    const deltaa = []
    const deltab = []
    let i = 0
    let j = 0
    let imax = lista.length
    let jmax = listb.length
    while (i < imax && j < jmax) {
        const a = lista[i]
        const b = listb[j]
        if (carddb[a.card].rank < carddb[b.card].rank) {
            deltaa.push({
                "card": a.card,
                "quantity": `+${a.quantity}`
            })
            deltab.push({
                "card": a.card,
                "quantity": `-${a.quantity}`
            })
            i++
        } else if (carddb[a.card].rank > carddb[b.card].rank) {
            deltaa.push({
                "card": b.card,
                "quantity": `-${b.quantity}`
            })
            deltab.push({
                "card": b.card,
                "quantity": `+${b.quantity}`
            })
            j++
        } else {
            // ranks are even, so cards are same. check quantity
            if (a.quantity > b.quantity) {
                delta = a.quantity - b.quantity
                deltaa.push({
                    "card": a.card,
                    "quantity": `-${delta}`
                })
                deltab.push({
                    "card": a.card,
                    "quantity": `+${delta}`
                })
            } else if (a.quantity < b.quantity) {
                delta = b.quantity - a.quantity
                deltaa.push({
                    "card": a.card,
                    "quantity": `+${delta}`
                })
                deltab.push({
                    "card": a.card,
                    "quantity": `-${delta}`
                })
            }
            i++; j++
        }
    }
    return [deltaa, deltab]
}

async function glimpse_delta() {
    reset_results()
    const dls = await get_dls()
    if (!dls) {
        show_delta_error("Couldn't get both decklists from Omnidex")
        return
    }
    const {p1, p2} = dls
    if (!p1 || !p2) {
        show_delta_error("Couldn't get one of the decklists from Omnidex")
        return
    }
    // TODO: set names properly
    document.querySelector(".d1.name").innerText = `player #${document.querySelector("#delta-p-1").value}`
    document.querySelector(".d2.name").innerText = `player #${document.querySelector("#delta-p-2").value}`
    
    // Calculate decklist deltas per section
    const [p1matd, p2matd] = calc_delta(p1.material, p2.material)
    const d1mat = document.querySelector(".d1.mat-deck .deck_gfx")
    for (const card_o of p1matd) {
        d1mat.appendChild(cardimg(card_o))
    }
    const d2mat = document.querySelector(".d2.mat-deck .deck_gfx")
    for (const card_o of p2matd) {
        d2mat.appendChild(cardimg(card_o))
    }

    const [p1maind, p2maind] = calc_delta(p1.main, p2.main)
    const d1main = document.querySelector(".d1.maindeck .deck_gfx")
    for (const card_o of p1maind) {
        d1main.appendChild(cardimg(card_o))
    }
    const d2main = document.querySelector(".d2.maindeck .deck_gfx")
    for (const card_o of p2maind) {
        d2main.appendChild(cardimg(card_o))
    }

    const [p1sided, p2sided] = calc_delta(p1.sideboard, p2.sideboard)
    const d1side = document.querySelector(".d1.sideboard .deck_gfx")
    for (const card_o of p1sided) {
        d1side.appendChild(cardimg(card_o))
    }
    const d2side = document.querySelector(".d2.sideboard .deck_gfx")
    for (const card_o of p2sided) {
        d2side.appendChild(cardimg(card_o))
    }
}

document.querySelector(".decklist-delta").addEventListener("submit", (evt) => {
    evt.preventDefault()
    glimpse_delta()
})
