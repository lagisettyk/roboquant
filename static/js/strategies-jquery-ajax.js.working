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
    $('#showList').html('<li><a href="#" id="simulate-1">BB_Spread_strategy</a>'
                         +'</li><li><a href="#" id="simulate-1">TN_strategy</a></li>'
                        );
  });

  $('#tickerList').on('click','#simulate-1',function(){
      var amount = $('#InitialCash').val();
      var drp = $('#reportrange2').data('daterangepicker');
      var stkticker = $('input.typeahead.tt-input').val();
      //alert("Inside the event #simulate-1: " + stkticker);
      //console.log("Selected Option:"+$(this).text());
      var strategy = $(this).text();
      //console.log(drp.startDate);
      //console.log("I am here....$$$$" + amount)
    $.ajax({
              url: '/strategies/backtest_results/?Ticker='+stkticker+'&strategy='+strategy+'&amount='+amount+"&stdate="+drp.startDate.toISOString()+"&enddate="+drp.endDate.toISOString(),
              type: 'GET',
              async: true,
              dataType: "json",
              beforeSend: function( xhr, status ) {
               //alert( "Before calling function" );
               //Indicates progress bar...
               $("*").css("cursor", "progress");
              }, 
              success: function (data) {
                console.log("Inside Success")
                //console.log(data)
                //var ticker = "AAPL"
                portseries = []
                portseries[0] = {name: "portfolio value", data: data.seriesData};
                portseries[1] = {name: "trades", data: data.flagData};
                displayPortfolioData(portseries, stkticker)
                bbseries = []
                bbseries[0] = {name: "price", data: data.price};
                bbseries[1] = {name: "upper", data: data.upper};
                bbseries[2] = {name: "middle", data: data.middle};
                bbseries[3] = {name: "lower", data: data.lower};
                bbseries[4] = {name: "rsi", data: data.rsi};
                bbseries[5] = {name: "macd", data: data.macd};
                displayBBData(bbseries,stkticker)

                emaseries = []
                emaseries[0] = {name: "price", data: data.price};
                emaseries[1] = {name: "ema fast", data: data.emafast};
                emaseries[2] = {name: "ema slow", data: data.emaslow};
                emaseries[3] = {name: "ema signal", data: data.emasignal};
                emaseries[4] = {name: "cashflow(3days)", data: data.cashflow_3days};
                emaseries[5] = {name: "volume", data: data.volume};
                emaseries[6] = {name: "vol MA 5 days", data: data.volsma5days};
                
                displayEMAData(emaseries,stkticker)

                adx_dmi_data = []
                adx_dmi_data[0] = {name: "price", data: data.price};
                adx_dmi_data[1] = {name: "adx", data: data.adx};
                adx_dmi_data[2] = {name: "dmi plus", data: data.dmiplus};
                adx_dmi_data[3] = {name: "dmi minus", data: data.dmiminus};
                display_ADX_DMI_Data(adx_dmi_data, stkticker)
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
               //Change back cursor to normal...
               $("*").css("cursor", "default");
              } 
        });
  });

  //var options = { $AutoPlay: true };
  var options = {
            $DragOrientation: 0, /// This is too make sure drag even does not trigger slide show...
            $ArrowNavigatorOptions: {
                $Class: $JssorArrowNavigator$,
                $ChanceToShow: 2
            }
  };
  var jssor_slider1 = new $JssorSlider$('slider1_container', options);
 


  function displayPortfolioData (dataList, ticker) {

      $('#container').highcharts('StockChart', {
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
                  text : ticker + ": Portfolio Performance",
                  floating: true,
                  align: 'left',
                  x: 75,
                  y: 70
              },

              series : [{
                  name : dataList[0].name,
                  data : dataList[0].data,
                  turboThreshold: 0, ///Speed up and make sure it supports more points
                  tooltip: {
                      valueDecimals: 2
                  },
                  id : 'dataseries'
             },{
                  type: 'flags',
                  name : dataList[1].name,
                  data : dataList[1].data,
                  turboThreshold: 0, ///Speed up and make sure it supports more points
                  tooltip: {
                      valueDecimals: 2
                  },
             }]
          });
    }

    function display_ADX_DMI_Data (dataList, ticker) {
      $('#container4').highcharts('StockChart', {
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
                  selected : 0
              },

              title : {
                  text : ticker + ": ADX & DMI Chart",
                  floating: true,
                  align: 'left',
                  x: 75,
                  y: 70
              },

               yAxis: [ { //--- primary yAxis
                          title: {
                              text: 'Price'
                          },
                          //min: 0,
                          height: '60%'
              },{ //--- secondary yAxis
                             title : {
                                text : 'Level'
                             },
                              top: '65%',
                              height: '35%',
                              offset: 0,
                              lineWidth: 2,
                              opposite: true
              }],

              //series: data,
              series : [{
                type: 'candlestick',
                color: '#000000',
                name : dataList[0].name,
                data : dataList[0].data,
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries1'
               },{
                yAxis: 1,
                color: '#000000',
                name : dataList[1].name,
                data : dataList[1].data,
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries2'
               },{
                yAxis: 1,
                color: '#006600',
                name : dataList[2].name,
                data : dataList[2].data,
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries3'
               },{
                yAxis: 1,
                color: '#CC3300',
                name : dataList[3].name,
                data : dataList[3].data,
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries4'
               }]
            });
    }


    function displayBBData (dataList, ticker) {
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
                  selected : 0
              },

              title : {
                  text : ticker + ": Bollinger Bands, MACD & RSI",
                  floating: true,
                  align: 'left',
                  x: 75,
                  y: 70
              },

               yAxis: [ { //--- primary yAxis
                          title: {
                              text: 'Price'
                          },
                          height: '45%'
              },{ //--- secondary yAxis
                     title : {
                        text : 'RSI'
                     },
                      min: 0,
                      max: 100,
                      top: '45%',
                      height: '35%',
                      lineWidth: 2,
                      plotLines : [{
                              value : 30,
                              color : 'red',
                              dashStyle : 'shortdash',
                              width : 2,
                              label : {
                                  text : 'minimum'
                              }
                        }, {
                            value : 70,
                            color : 'red',
                            dashStyle : 'shortdash',
                            width : 2,
                            label : {
                                text : 'maximum'
                            }
                      }],
                      //opposite: true
              },{ //--- terinary yAxis
                      title: {
                          text: 'MACD'
                      },
                      //min: 0,
                      top: '85%',
                      height: '20%',
                      opposite: true
              }],

              //series: data,
              series : [{
                type: 'candlestick',
                color: '#000000',
                name : dataList[0].name,
                data : dataList[0].data,
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries1'
               },{
                color: '#CC00CC',
                name : dataList[1].name,
                data : dataList[1].data,
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries2'
               },{
                color: '#CC0000',
                name : dataList[2].name,
                data : dataList[2].data,
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries3'
               },{
                color: '#CC00CC',
                name : dataList[3].name,
                data : dataList[3].data,
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries4'
               },{
                yAxis: 1,
                color: '#FF9933',
                name : dataList[4].name,
                data : dataList[4].data,
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries5'
               },{
                yAxis: 2,
                color: '#0033CC',
                name : dataList[5].name,
                data : dataList[5].data,
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries6'
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
                  selected : 0
              },

              yAxis: [ { //--- primary yAxis
                          title: {
                              text: 'EMA'
                          },
                          height: '40%'
              },{ //--- secondary yAxis
                      title: {
                          text: 'cashflow'
                      },
                      //min: 0,
                      top: '45%',
                      height: '40%',
                      opposite: true
              },{ //--- terinary yAxis
                       title : {
                          text : 'Volume'
                       },
                        min: 0,
                        top: '85%',
                        height: '35%',
                        offset: 0,
                        opposite: true
              }],

              title : {
                  text : ticker + ": EMA Data",
                  floating: true,
                  align: 'left',
                  x: 75,
                  y: 70
              },

              //series: data,
              series : [{
                type: 'candlestick',
                color: '#000000',
                yAxis: 0,
                name : dataList[0].name,
                data : dataList[0].data,
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries1'
               },{
                yAxis: 0,
                name : dataList[1].name,
                data : dataList[1].data,
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries1'
               },{
                yAxis: 0,
                name : dataList[2].name,
                data : dataList[2].data,
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries2'
               },{
                yAxis: 0,
                name : dataList[3].name,
                data : dataList[3].data,
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries3'
               },{
                 yAxis: 1,
                 color: '#0033CC',
                 name : dataList[4].name,
                 data : dataList[4].data,
                 turboThreshold: 0, ///Speed up and make sure it supports more points
                 tooltip: {
                    valueDecimals: 2
                 },
                 id : 'dataseries5'
               },{
                yAxis: 2,
                type: 'column',
                name : dataList[5].name,
                data : dataList[5].data,
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries4'
               },{
                yAxis: 2,
                color: '#000000',
                name : dataList[6].name,
                data : dataList[6].data,
                turboThreshold: 0, ///Speed up and make sure it supports more points
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


/// Typeahead realted functionality...........
var substringMatcher = function(strs) {
  return function findMatches(q, cb) {
    var matches, substringRegex;
 
    // an array that will be populated with substring matches
    matches = [];
 
    // regex used to determine if a string contains the substring `q`
    substrRegex = new RegExp(q, 'i');
 
    // iterate through the pool of strings and for any string that
    // contains the substring `q`, add it to the `matches` array
    $.each(strs, function(i, str) {
      if (substrRegex.test(str)) {
        matches.push(str);
      }
    });
 
    cb(matches);
  };
};
 
var tickers = ['AAPL', 'AMZN', 'FDX', 'MA', 'NFLX', 'OCR', 'SPY', 'NXPI', 'CVS', 'UNP', 'GILD', 'VRX', 'ACT', 
   'GOOGL', 'CF', 'URI', 'CP', 'WHR', 'IWM', 'UNH', 'VIAB', 'FLT', 'ODFL', 'GD', 'XLF', 'ALL', 'V'];
 
$('#Ticker .typeahead').typeahead({
  hint: true,
  highlight: true,
  minLength: 1
},
{
  name: 'tickers',
  source: substringMatcher(tickers)
});



}); //end of ready function