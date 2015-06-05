$(document).ready( function() {

    // JQuery code to related to rango application to be added in here.
    // For all the JQury commands they follow a similar pattern: Select & Act
    // Select an element, and then act on the element
    // Code aalso reflects ajax functions...

    /////block corrosponds too date-range picker....
    $('#reportrange2 span').html(moment().subtract(29, 'days').format('MMMM D, YYYY') + ' - ' + moment().format('MMMM D, YYYY'));
    $("#reportrange2").daterangepicker({
                    format: 'MM/DD/YYYY',
                    minDate: '01/01/2005',
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



  function displayRedisData (data, ticker) {

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

  
  //##### to do.. Need to get dynamic list from dJango vieww
  $('#tickerList').on('click', '#dLabel', function(){
    console.log("inside dLabel")
    $('#showList').empty()
    $('#showList').html('<li><a href="#" id="simulate-1">AAPL</a>'
                         +'</li><li><a href="#" id="simulate-1">AMZN</a></li>'
                         +'</li><li><a href="#" id="simulate-1">FDX</a></li>'
                         +'</li><li><a href="#" id="simulate-1">MA</a></li>'
                         +'</li><li><a href="#" id="simulate-1">NFLX</a></li>'
                         +'</li><li><a href="#" id="simulate-1">OCR</a></li>'
                         +'</li><li><a href="#" id="simulate-1">SPY</a></li>'
                         +'</li><li><a href="#" id="simulate-1">NXPI</a></li>'
                         +'</li><li><a href="#" id="simulate-1">CVS</a></li>'
                         +'</li><li><a href="#" id="simulate-1">UNP</a></li>'
                         +'</li><li><a href="#" id="simulate-1">GILD</a></li>'
                         +'</li><li><a href="#" id="simulate-1">VRX</a></li>'
                         +'</li><li><a href="#" id="simulate-1">ACT</a></li>'
                         +'</li><li><a href="#" id="simulate-1">GOOGL</a></li>'
                         +'</li><li><a href="#" id="simulate-1">CF</a></li>'
                         +'</li><li><a href="#" id="simulate-1">URI</a></li>'
                         +'</li><li><a href="#" id="simulate-1">CP</a></li>'
                         +'</li><li><a href="#" id="simulate-1">WHR</a></li>'
                         +'</li><li><a href="#" id="simulate-1">IWM</a></li>'
                         +'</li><li><a href="#" id="simulate-1">UNH</a></li>'
                         +'</li><li><a href="#" id="simulate-1">VIAB</a></li>'
                         +'</li><li><a href="#" id="simulate-1">FLT</a></li>'
                         +'</li><li><a href="#" id="simulate-1">ODFL</a></li>'
                         +'</li><li><a href="#" id="simulate-1">GD</a></li>'
                         +'</li><li><a href="#" id="simulate-1">XLF</a></li>'
                         +'</li><li><a href="#" id="simulate-1">ALL</a></li>'
                         +'</li><li><a href="#" id="simulate-1">V</a></li>'
                        );
  });

  $('#tickerList').on('click','#simulate-1',function(){
      var amount = $('#InitialCash').val();
      var drp = $('#reportrange2').data('daterangepicker');
      //alert("Inside the even #simulate-1")
      console.log("Selected Option:"+$(this).text())
      var stockticker = $(this).text()
      //console.log(drp.startDate);
      //console.log("I am here....$$$$" + amount)
    $.ajax({
              url: '/strategies/backtest_results/?Ticker='+stockticker+'&amount='+amount+"&stdate="+drp.startDate.toISOString()+"&enddate="+drp.endDate.toISOString(),
              type: 'GET',
              async: true,
              dataType: "json",
              success: function (data) {
                console.log("Inside Success")
                //console.log(data)
                //var ticker = "AAPL"
                displayPortfolioData(data.seriesData, stockticker)
                bbseries = []
                bbseries[0] = {name: "upper", data: data.upper};
                bbseries[1] = {name: "middle", data: data.middle};
                bbseries[2] = {name: "lower", data: data.lower};
                bbseries[3] = {name: "price", data: data.price};
                bbseries[4] = {name: "flagData", data: data.flagData};
                displayBBData(bbseries,stockticker)
                emaseries = []
                emaseries[0] = {name: "rsi", data: data.rsi};
                emaseries[1] = {name: "ema fast", data: data.emafast};
                emaseries[2] = {name: "ema slow", data: data.emaslow};
                emaseries[3] = {name: "ema signal", data: data.emasignal};
                displayEMAData(emaseries,stockticker)
                //displayInstrumentData(data.instrumentDetails, data.flagData, stockticker)
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
 


  function displayPortfolioData (data, ticker) {

      $('#container').highcharts('StockChart', {
              rangeSelector : {
                  selected : 5
              },

              title : {
                  text : ticker +' portfolio value'
              },

              series : [{
                  name : ticker,
                  data : data,
                  tooltip: {
                      valueDecimals: 2
                  },
                  id : 'dataseries'
             }]
          });
    }

    function displayBBData (dataList, ticker) {
      //console.log(dataList[4].name)
      //console.log(dataList[4].data)
      $('#container3').highcharts('StockChart', {

             legend: {
                    enabled: true,
                    align: 'right',
                    backgroundColor: '#FCFFC5',
                    borderColor: 'black',
                    borderWidth: 2,
                    layout: 'vertical',
                    verticalAlign: 'top',
                    y: 100,
                    shadow: true
              },
              rangeSelector : {
                  selected : 5
              },

              title : {
                  text : "Bollinger Bands"
              },

              //series: data,
              series : [{
                name : dataList[0].name,
                data : dataList[0].data,
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries1'
               },{
                name : dataList[1].name,
                data : dataList[1].data,
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries2'
               },{
                name : dataList[2].name,
                data : dataList[2].data,
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries3'
               },{
                name : dataList[3].name,
                type: 'candlestick',
                data : dataList[3].data,
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries4'
               },{
                        type : 'flags',
                        name : 'trades',
                        data : dataList[4].data,
                        //onSeries : 'dataseries4',
                        shape : 'squarepin',
                        width : 16
              }]
            });
    }


    function displayEMAData (dataList, ticker) {
      $('#container2').highcharts('StockChart', {
             
              legend: {
                    enabled: true,
                    align: 'right',
                    backgroundColor: '#FCFFC5',
                    borderColor: 'black',
                    borderWidth: 2,
                    layout: 'vertical',
                    verticalAlign: 'top',
                    y: 100,
                    shadow: true
              },
  
              rangeSelector : {
                  selected : 5
              },

              title : {
                  text : "EMA Data"
              },

              /*plotOptions: {
                  series: {
                    events: {
                        legendItemClick: function(event) {
                            var visibility = this.visible ? 'visible' : 'hidden';
                            if (!confirm('The series is currently '+ 
                                         visibility +'. Do you want to change that?')) {
                                return false;
                            }
                        }
                    }
                  }
              },*/

              //series: data,
              series : [{
                name : dataList[0].name,
                data : dataList[0].data,
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries1'
               },{
                name : dataList[1].name,
                data : dataList[1].data,
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries2'
               },{
                name : dataList[2].name,
                data : dataList[2].data,
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries3'
               },{
                name : dataList[3].name,
                data : dataList[3].data,
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries4'
               }]
            });
    }

    function displayReturnData (data, ticker) {

      //console.log("inside displayData")
      //var flagdata 
      //console.log(data)
      //console.log(flagdata)
      $('#container3').highcharts('StockChart', {
              rangeSelector : {
                  selected : 5
              },

              title : {
                  text : ticker +' cumulative returns'
              },

              series : [{
                  name : ticker,
                  data : data,
                  tooltip: {
                      valueDecimals: 2
                  },
                  id : 'dataseries'
             }]
          });
    }

    function displayInstrumentData (data, flagdata, ticker) {
      $('#container2').highcharts('StockChart', {
              rangeSelector : {
                  selected : 5
              },

              title : {
                  text : ticker +' positions'
              },

              series : [{
                  name : ticker,
                  data : data,
                  tooltip: {
                      valueDecimals: 2
                  },
                  id : 'dataseries'
               // the event marker flags
            }, {
                type : 'flags',
                data : flagdata,
                onSeries : 'dataseries',
                shape : 'circlepin',
                width : 16
            }]
          });
    }

  $('#action-1').click(function () {
    $.ajax({
              url: '/strategies/hichart_redis/?Ticker=AAPL',
              type: 'GET',
              async: true,
              dataType: "json",
              success: function (data) {
                console.log("Inside Success")
                var ticker = "AAPL"
                //console.log(data.seriesData)
                displayRedisData(data, ticker);
                //displayData(data.seriesData, data.flagData, ticker)
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
                displayRedisData(data, ticker);
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
                displayRedisData(data, ticker);
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
                displayRedisData(data, ticker);
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
                displayRedisData(data, ticker);
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
                displayRedisData(data, ticker);
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