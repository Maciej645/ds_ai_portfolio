# Projekt aplikacji estymującej czas użytkownika w półmaratonie

Na podstawie danych z półmaratonu Wrocław 2024 opracowałem w jupyter lab model regresyjny do predykcji czasu w półmaratonie na podstawie danych wsadowych : wiek, płeć, czas na 5 km. W oparciu o model predykcyjny zaprojektowałem aplikację do estymacji czasu użytkownika wraz z prezentowaniem wyniku na tle innych uczestników półmaratonu Wrocław 2024.Zapraszam do zapoznania sie z projektem


<a href="halfmarathon_city_9.1.ipynb" class="md-button md-button--primary">Pobierz Notebook</a>

<iframe
    id="content"
    src="halfmarathon_city_9.1.html"
    width="100%"
    style="border:1px solid black;overflow:hidden;"
></iframe>
<script>
function resizeIframeToFitContent(iframe) {
    iframe.style.height = (iframe.contentWindow.document.documentElement.scrollHeight + 50) + "px";
    iframe.contentDocument.body.style["overflow"] = 'hidden';
}
window.addEventListener('load', function() {
    var iframe = document.getElementById('content');
    resizeIframeToFitContent(iframe);
});
window.addEventListener('resize', function() {
    var iframe = document.getElementById('content');
    resizeIframeToFitContent(iframe);
});
</script