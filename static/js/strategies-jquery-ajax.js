$(document).ready( function() {

    // JQuery code to related to rango application to be added in here.
    // For all the JQury commands they follow a similar pattern: Select & Act
    // Select an element, and then act on the element
    // Code aalso reflects ajax functions...

    /////block corrosponds too date-range picker....
    $('#reportrange2 span').html(moment().subtract(29, 'days').format('MMMM D, YYYY') + ' - ' + moment().format('MMMM D, YYYY'));
    $("#reportrange2").daterangepicker({
                    format: 'MM/DD/YYYY',
                    minDate: '01/01/2012',
                    maxDate: '12/31/2014',
                    dateLimit: { days: 250 },
                  }, function(start, end, label) {
                    //alert("You clicked the button using JQuery!");
                    console.log(start.toISOString(), end.toISOString(), label);
                    $('#reportrange2 span').html(start.format('MMMM D, YYYY') + ' - ' + end.format('MMMM D, YYYY'));
                  });


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


    function displayData (data, ticker) {

      console.log("inside displayData")
      //console.log(data)
      $('#container').highcharts('StockChart', {
              rangeSelector : {
                  selected : 5
              },

              title : {
                  text : ticker +' Stock Price'
              },

              series : [{
                  name : ticker,
                  data : data,
                  tooltip: {
                      valueDecimals: 2
                  }
              }]
          });
    }

    /*
    $('#highstock-btn').click(function(){
      $.ajax({
            url: '/strategies/hichart_quandl/',
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
    }); */

  $('#action-1').click(function () {
    $.ajax({
              url: '/strategies/hichart_redis/?Ticker=AAPL',
              type: 'GET',
              async: true,
              dataType: "json",
              success: function (data) {
                console.log("Inside Success")
                var ticker = "AAPL"
                displayData(data, ticker);
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
               //alert( "The request is complete!" );
              } 
        });
    });

  $('#action-2').click(function () {
    $.ajax({
              url: '/strategies/hichart_redis/?Ticker=MSFT',
              type: 'GET',
              async: true,
              dataType: "json",
              success: function (data) {
                console.log("Inside Success")
                var ticker = "MSFT"
                displayData(data, ticker);
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
               //alert( "The request is complete!" );
              } 
        });
    });
   $('#action-3').click(function () {
    $.ajax({
              url: '/strategies/hichart_redis/?Ticker=GS',
              type: 'GET',
              async: true,
              dataType: "json",
              success: function (data) {
                console.log("Inside Success")
                var ticker = "GS"
                displayData(data, ticker);
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
               //alert( "The request is complete!" );
              } 
        });
    });

    $('#action-4').click(function () {
    $.ajax({
              url: '/strategies/hichart_quandl/?Ticker=AAPL',
              type: 'GET',
              async: true,
              dataType: "json",
              success: function (data) {
                console.log("Inside Success")
                var ticker = "AAPL"
                displayData(data, ticker);
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
               //alert( "The request is complete!" );
              } 
        });
    });

    $('#action-5').click(function () {
    $.ajax({
              url: '/strategies/hichart_quandl/?Ticker=MSFT',
              type: 'GET',
              async: true,
              dataType: "json",
              success: function (data) {
                console.log("Inside Success")
                var ticker = "MSFT"
                displayData(data, ticker);
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
               //alert( "The request is complete!" );
              } 
        });
    });

    $('#action-6').click(function () {
    $.ajax({
              url: '/strategies/hichart_quandl/?Ticker=GS',
              type: 'GET',
              async: true,
              dataType: "json",
              success: function (data) {
                console.log("Inside Success")
                var ticker = "GS"
                displayData(data, ticker);
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
               //alert( "The request is complete!" );
              } 
        });
    });

    $('#simulate-1').click(function () {
      var amount = $('#InitialCash').val();
      //alert("You clicked the button using JQuery!");
      var drp = $('#reportrange2').data('daterangepicker');
      console.log(drp.startDate);
      console.log("I am here....$$$$" + amount)
    $.ajax({
              url: '/strategies/backtest_results/?Ticker=AAPL'+'&amount='+amount+"&stdate="+drp.startDate.toISOString()+"&enddate="+drp.endDate.toISOString(),
              type: 'GET',
              async: true,
              dataType: "json",
              success: function (data) {
                console.log("Inside Success")
                var ticker = "AAPL"
                displayData(data, ticker);
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
               //alert( "The request is complete!" );
              } 
        });
    });

    $('#simulate-2').click(function () {
      var amount = $('#InitialCash').val();
      var drp = $('#reportrange2').data('daterangepicker');
    $.ajax({
              url: '/strategies/backtest_results/?Ticker=MSFT'+'&amount='+amount+"&stdate="+drp.startDate.toISOString()+"&enddate="+drp.endDate.toISOString(),
              type: 'GET',
              async: true,
              dataType: "json",
              success: function (data) {
                console.log("Inside Success")
                var ticker = "MSFT"
                displayData(data, ticker);
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
               //alert( "The request is complete!" );
              } 
        });
    });

    $('#simulate-3').click(function () {
      var amount = $('#InitialCash').val();
      var drp = $('#reportrange2').data('daterangepicker');
    $.ajax({
              url: '/strategies/backtest_results/?Ticker=GS'+'&amount='+amount+"&stdate="+drp.startDate.toISOString()+"&enddate="+drp.endDate.toISOString(),
              type: 'GET',
              async: true,
              dataType: "json",
              success: function (data) {
                console.log("Inside Success")
                var ticker = "GS"
                displayData(data, ticker);
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
               //alert( "The request is complete!" );
              } 
        });
    });

}); //end of ready function