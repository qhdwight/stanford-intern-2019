const chartLineColors = [
    'rgba(255, 99, 132, 1)',
    'rgba(54, 162, 235, 1)',
    'rgba(255, 206, 86, 1)',
    'rgba(75, 192, 192, 1)',
    'rgba(153, 102, 255, 1)',
    'rgba(255, 159, 64, 1)'
];

const chartBackgroundColors = [
    'rgba(255, 99, 132, 0.2)',
    'rgba(54, 162, 235, 0.2)',
    'rgba(255, 206, 86, 0.2)',
    'rgba(75, 192, 192, 0.2)',
    'rgba(153, 102, 255, 0.2)',
    'rgba(255, 159, 64, 0.2)'
];

function getChartLineColor(index) {
    index %= chartLineColors.length;
    return chartLineColors[index];
}

function getChartBackgroundColor(index) {
    index %= chartBackgroundColors.length;
    return chartBackgroundColors[index];
}

function formatBytes(bytes, decimals) {
    if (bytes == 0) return '0 Bytes';
    const k = 1024,
        dm = decimals <= 0 ? 0 : decimals || 2,
        sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'],
        i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function formatCount(number, formatType) {
    if (formatType === 'regular') {
        return Math.floor(number).toLocaleString();
    } else if (formatType === 'space') {
        return formatBytes(number, 1);
    }
}

$(document).ready(function () {
    $('.counter[data-count]').fadeTo(0, 0).fadeTo(1000, 1).each(function () {
        const $this = $(this), countTo = $this.attr('data-count'), formatType = $this.attr('format');
        $({finalNumber: $this.text()}).animate({
                count: countTo
            },
            {
                duration: 1500,
                easing: 'swing',
                step: function () {
                    $this.text(formatCount(this.count, formatType))
                },
                complete: this.step
            });
    });
});
