$(document).ready( function() {

    // JQuery code to related to rango application to be added in here.
    // For all the JQury commands they follow a similar pattern: Select & Act
    // Select an element, and then act on the element
    // Code aalso reflects ajax functions...

    $("#about-btn").addClass('btn btn-primary');

    $("#about-btn").click( function(event) {
    alert("You clicked the button using JQuery!");
	  });

    //Adding Graphic related examples....

    $("#matplotlib-btn").addClass('btn btn-primary');

    $("#matplotlib-btn").click( function() {
      //alert("You clicked the button using JQuery!");
     $('#content').html('<img id="loader-img" alt="" src="simple.png" height="400" align="center" />');
    });

    $("#highstock-btn").addClass('btn btn-primary');


/*
    $("#highstock-btn").click( function () {
      //alert("You clicked the button using JQuery! for displaying highstock");
        var seriesOptions = [],
        seriesCounter = 0,
        names = ['MSFT', 'AAPL', 'GOOG'],
        // create the chart when all data is loaded
        createChart = function () {

            $('#container').highcharts('StockChart', {

                rangeSelector: {
                    selected: 4
                },

                yAxis: {
                    labels: {
                        formatter: function () {
                            return (this.value > 0 ? ' + ' : '') + this.value + '%';
                        }
                    },
                    plotLines: [{
                        value: 0,
                        width: 2,
                        color: 'silver'
                    }]
                },

                plotOptions: {
                    series: {
                        compare: 'percent'
                    }
                },

                tooltip: {
                    pointFormat: '<span style="color:{series.color}">{series.name}</span>: <b>{point.y}</b> ({point.change}%)<br/>',
                    valueDecimals: 2
                },

                series: seriesOptions
            });
        };

    $.each(names, function (i, name) {

        $.getJSON('http://www.highcharts.com/samples/data/jsonp.php?filename=' + name.toLowerCase() + '-c.json&callback=?',    function (data) {

            seriesOptions[i] = {
                name: name,
                data: data
            };

            // As we're loading the data asynchronously, we don't know what order it will arrive. So
            // we keep a counter and create the chart when all the data is loaded.
            seriesCounter += 1;

            if (seriesCounter === names.length) {
                createChart();
            }
        });
    });

  });

*/


	$("#about-btn").click( function(event) {
		msgstr = $("#msg").html()
        msgstr = msgstr + " Kiran!!!"
        $("#msg").html(msgstr)
 	});

    $("p").hover( function() {
            $(this).css('color', 'red');
    },
    function() {
            $(this).css('color', 'blue');
    });


    // Example for ajax functionality with JQuery...
 	$('#likes').click( function(){
	    var catid;
	    catid = $(this).attr("data-catid");
	    $.get('/rango/like_category/', {category_id: catid}, function(data){
	               $('#like_count').html(data);
	               $('#likes').hide();
	    });
	});

	$('#suggestion').keyup( function(){
		var query;
		query = $(this).val();
		$.get('/rango/suggest_category/', {suggestion: query}, function(data){
			$('#cats').html(data);
		});// end block of get frunction
	}); // end block for keyup function...

	// JQuery for adding auto page to the category.html...
	/*$('.rango-add').click( function(){
		//alert("You clicked the button using JQuery! rango-add");
		var catid = $(this).attr("data-catid");
		var url = $(this).attr("data-url")
		var title = $(this).attr("data-title")
		$.get('/rango/auto_add_page/', {category_id: catid, url:url, title:title}, function(data){
			$('#pages').html(data);
          	me.hide();
		)};
	});//end block for click function...*/

   $('.rango-add').click(function(){
   	  //alert("You clicked the button using JQuery! rango-add");
   	  var catid = $(this).attr("data-catid");
      var url = $(this).attr("data-url");
      var desc = $(this).attr("data-desc")
   	  $.get('/rango/auto_add_page', {category_id: catid, url: url, title: desc}, function(data){
        $('#pages').html(data);
        me.hide();
      });
    });

    /*
    $('#highstock-btn').click(function(){
      //alert("You clicked the button using JQuery! highstock button");
      //$.getJSON('http://www.highcharts.com/samples/data/jsonp.php?filename=aapl-c.json&callback=?', function(data){
      $.get('/rango/hichart_quandl/', function(data){
        console.log(data)
       $('#container').highcharts('StockChart', {
              rangeSelector : {
                  selected : 1
              },

              title : {
                  text : 'AAPL Stock Price'
              },

              series : [{
                  name : 'AAPL',
                  data : $('#container').attr("data-hicharts"),
                  tooltip: {
                      valueDecimals: 2
                  }
              }]
          });
      });
        
    }); */

    function displayData (data) {

      console.log("inside displayData")
      //console.log(data)
      $('#container').highcharts('StockChart', {
              rangeSelector : {
                  selected : 1
              },

              title : {
                  text : 'AAPL Stock Price'
              },

              series : [{
                  name : 'AAPL',
                  data : data,
                  tooltip: {
                      valueDecimals: 2
                  }
              }]
          });
    }

    $('#highstock-btn').click(function(){
      $.ajax({
            url: '/rango/hichart_quandl/',
            type: 'GET',
            async: true,
            dataType: "json",
            success: function (data) {
              console.log("Inside Success")
              displayData(data);
            },
            // Code to run if the request fails; the raw request and
    // status codes are passed to the function
            error: function( xhr, status, errorThrown ) {
                  alert( "Sorry, there was a problem!" );
                  console.log( "Error: " + errorThrown );
                  console.log( "Status: " + status );
                  console.dir( xhr );
            },
            // Code to run regardless of success or failure
            complete: function( xhr, status ) {
             alert( "The request is complete!" );
            } 
      });
    });


}); //end of ready function