function capitalize(string) {
  return string.charAt(0).toUpperCase() + string.slice(1);
}
function formatFilename(filename){
  var split = filename.replace('.json', '').split('-');
  return 'DB: ' + capitalize(split[0]) + ', Strategy: ' + split[1] + ', Cache: ' + split[2];
}
function formatResult(name){
  return capitalize(name.replace('-', ' '));
}

(function($){
  var filenames = [
    'unknown-unknown-unknown.json',
    'cockroach-lock-cache.json',
    'cockroach-lock-nocache.json',
    'cockroach-none-cache.json',
    'cockroach-none-nocache.json',
    'postgresql-lock-cache.json',
    'postgresql-lock-nocache.json',
    'postgresql-resolve-cache.json',
    'postgresql-resolve-nocache.json'
  ];
  var allResults = [];
  var buildNumber = 0;
  while(true){
    var buildResults = {};
    filenames.forEach(function(filename){
      $.ajax({
        url: 'results/' + buildNumber + '/' + filename,
        async: false
      }).done(function(result){
        buildResults[filename] = result;
      }).fail(function(){
      });
    });
    if(Object.keys(buildResults).length > 0){
      allResults.push({
        buildNumber: buildNumber,
        results: buildResults
      });
    }else if(buildNumber > 8){
      break;
    }
    buildNumber += 1;
  }

  google.charts.load('current', {'packages':['corechart', 'bar']});
  // Set a callback to run when the Google Visualization API is loaded.
  google.charts.setOnLoadCallback(drawCharts);

  allResults.reverse();

  // Callback that creates and populates a data table,
  function drawCharts() {
    allResults.forEach(function(result){
      var $div = $('<div class="result"/>');
      $('.results').append($div);

      $div.append('<h3>Build number: ' + result.buildNumber + '</h3>');
      $.each(result.results, function(filename, file_results){
        $div.append('<h4>Type: ' + formatFilename(filename) + '</h4>');
        var data = [['Test type', 'Total/sec', 'Updates/sec', 'Writes/sec', 'Retries/sec']];

        $.each(file_results.data, function(type, value){
          var reads = value.requests - value.updates - value.writes;
          data.push([
            formatResult(type),
            Math.round(reads / value.duration),
            Math.round(value.updates / value.duration),
            Math.round(value.writes / value.duration),
            Math.round(value.retries / value.duration)
          ]);
        });

        var options = {
          chart: {
            title: 'Requests/Second',
            subtitle: 'Total, Updates, Writes, Retries',
          },
          isStacked: true,
          series: {
            0:{color: '#053492'},
            1:{color: '#b16d00'},
            2:{color: '#a70b0b'},
            3:{color: '#510096'}
          }
        };

        var $chartContainer = $('<div class="chart" style="width: 100%; height: 300px;"/>');
        $div.append($chartContainer);
        var chart = new google.charts.Bar($chartContainer[0]);
        chart.draw(google.visualization.arrayToDataTable(data), google.charts.Bar.convertOptions(options));
      });
    });
  }

})(jQuery);
