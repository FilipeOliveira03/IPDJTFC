function registarPopup() {
    let popup = document.getElementsByClassName('instalacaoformpopup')[0];
    popup.style.visibility = "visible"
}


window.addEventListener('load', function () {
    document.getElementById("popup").addEventListener("click", function (e) {
        e = window.event || e;
        if (this === e.target) {
            // put your code here
            let popup = document.getElementsByClassName('instalacaoformpopup')[0];
            popup.style.visibility = "hidden"
        }
    });
})