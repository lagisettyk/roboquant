$(document).ready( function() {


  /// Functions related to handsontable .....

  // Instead of creating a new Handsontable instance
    // with the container element passed as an argument,
    // you can simply call .handsontable method on a jQuery DOM object.
  var $container = $("#example1");
  
  function BindData(data) {
    $container.handsontable({
      //data: getData(),
      data: data,
      rowHeaders: true,
      colHeaders: true,
      contextMenu: true
    });
  }

  $("#sList").on('click', '#stratLabel', function(event) {
    alert("You clicked the button xxxList using JQuery!");
    $('#showStratList').empty()
    $('#showStratList').html('<li><a href="#" id="Simulate">Abhi-26</a>'
                         +'</li><li><a href="#" id="Simulate">CBOE-r100</a></li>'
                         +'</li><li><a href="#" id="Simulate">SP-500</a></li>'
                         +'</li><li><a href="#" id="Simulate">CBOE-r1000</a></li>'
                         +'</li><li><a href="#" id="Simulate">CBOE-ALL</a></li>'
                         +'</li><li><a href="#" id="Simulate">SP-500-CBOE-r1000</a></li>'
                         +'</li><li><a href="#" id="Simulate">SP-100</a></li>'
                        );
  });

  $('#sList').on('click','#Simulate',function(){
      var amount = $('#InitialCash').val();
      var drp = $('#reportrange2').data('daterangepicker');
      var rank = $('#rank').val();
      var strategy = $(this).text();
      var jobid = "NEW" /// This is to indicate new vs existing job polling...
      //alert( "Initializing Portfolio simulation... rank: "+rank );
      var intervalId = setInterval(function(){
          //Set cursor to processing....
          $("*").css("cursor", "progress");
          $.ajax({
                  url: '/strategies/backtest_portfolio/?strategy='+strategy+'&jobid='+jobid+'&amount='+amount+'&rank='+rank+"&stdate="+drp.startDate.toISOString()+"&enddate="+drp.endDate.toISOString(),
                  type: 'GET',
                  async: true,
                  dataType: "json",
                  beforeSend: function( xhr, status ) {
                           //alert( "Before calling function" );
                           //Indicates progress bar...
                           $("*").css("cursor", "progress");
                  }, 
                  success: function (data) {
                    if (data.jobstatus == "SUCCESS")
                    {
                        //// CLear the interval & set back the cursor...
                        clearInterval(intervalId); 
                        $("*").css("cursor", "default");
                        
                        console.log("Inside Success");
                        /*
                        portseries = []
                        portseries[0] = {name: "portfolio value", data: data.seriesData};
                        portseries[1] = {name: "trades", data: data.flagData};
                        portseries[2] = {name: "trades", data: data.cumulativereturns};
                        */
                        //displayPortfolioSimulation(portseries)
                        BindData(data.seriesData)
                    }
                    else
                    {
                      /// Let set interval make another calll with the returned jobid via status
                      jobid = data.jobstatus
                      //alert( "Inside polling loop...: " + jobid );
                    } 
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
                  complete: function( data, xhr, status ) {
                   //alert( "The request is complete!" );
                  } 
            });
      }, 3000); /// interval function.....
  });



  // JQuery code to related to rango application to be added in here.
  // For all the JQury commands they follow a similar pattern: Select & Act
  // Select an element, and then act on the element
  // Code aalso reflects ajax functions...

  /////block corrosponds too date-range picker....
  $('#reportrange2 span').html(moment().subtract(29, 'days').format('MMMM D, YYYY') + ' - ' + moment().format('MMMM D, YYYY'));
  $("#reportrange2").daterangepicker({
                  format: 'MM/DD/YYYY',
                  minDate: '01/01/2005',
                  maxDate: '12/31/2020',
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

  $('#strategyList').on('click', '#dLabel', function(){
    console.log("inside dLabel")
    $('#showList').empty()
    $('#showList').html('<li><a href="#" id="port_simulate">Abhi-26</a>'
                         +'</li><li><a href="#" id="port_simulate">CBOE-r100</a></li>'
                         +'</li><li><a href="#" id="port_simulate">SP-500</a></li>'
                         +'</li><li><a href="#" id="port_simulate">CBOE-r1000</a></li>'
                         +'</li><li><a href="#" id="port_simulate">CBOE-ALL</a></li>'
                         +'</li><li><a href="#" id="port_simulate">SP-500-CBOE-r1000</a></li>'
                         +'</li><li><a href="#" id="port_simulate">SP-100</a></li>'
                        );
  });

  $('#strategyList').on('click','#port_simulate',function(){
      var amount = $('#InitialCash').val();
      var drp = $('#reportrange2').data('daterangepicker');
      var rank = $('#rank').val();
      var strategy = $(this).text();
      var jobid = "NEW" /// This is to indicate new vs existing job polling...
      //alert( "Initializing Portfolio simulation... rank: "+rank );
      var intervalId = setInterval(function(){
          //Set cursor to processing....
          $("*").css("cursor", "progress");
          $.ajax({
                  url: '/strategies/backtest_portfolio/?strategy='+strategy+'&jobid='+jobid+'&amount='+amount+'&rank='+rank+"&stdate="+drp.startDate.toISOString()+"&enddate="+drp.endDate.toISOString(),
                  type: 'GET',
                  async: true,
                  dataType: "json",
                  beforeSend: function( xhr, status ) {
                           //alert( "Before calling function" );
                           //Indicates progress bar...
                           $("*").css("cursor", "progress");
                  }, 
                  success: function (data) {
                    if (data.jobstatus == "SUCCESS")
                    {
                        //// CLear the interval & set back the cursor...
                        clearInterval(intervalId); 
                        $("*").css("cursor", "default");
                        
                        console.log("Inside Success");
                        portseries = []
                        portseries[0] = {name: "portfolio value", data: data.seriesData};
                        portseries[1] = {name: "trades", data: data.flagData};
                        portseries[2] = {name: "trades", data: data.cumulativereturns};
                        displayPortfolioSimulation(portseries)
                    }
                    else
                    {
                      /// Let set interval make another calll with the returned jobid via status
                      jobid = data.jobstatus
                      //alert( "Inside polling loop...: " + jobid );
                    } 
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
                  complete: function( data, xhr, status ) {
                   //alert( "The request is complete!" );
                   //Change back cursor to normal...
                   /*if (data.jobstatus != "SUCCESS")
                    {
                       $("*").css("cursor", "progress");
                    }
                    else
                    {
                        $("*").css("cursor", "default");
                    }*/
                  } 
            });
      }, 3000); /// interval function.....
  });

  function displayPortfolioSimulation (dataList) {
    //insideChart1 = true;
    var chart1 = new Highcharts.StockChart({
     chart: {
                        renderTo: $('#port_container')[0]
                      },
              /*xAxis: {
                events: {
                             afterSetExtremes: function() {
                              //alert( "Inside the event box....");
                              if (!this.chart.options.chart.isZoomed) {
                                    var xMin = this.chart.xAxis[0].min;
                                    var xMax = this.chart.xAxis[0].max;
                                   
                                   ///Make sure to avoid recursive loop set them to true...
                                     chart2.options.chart.isZoomed = true;
                                     chart3.options.chart.isZoomed = true;
                                     chart4.options.chart.isZoomed = true;

                                    chart2.xAxis[0].setExtremes(xMin, xMax, true);
                                    chart3.xAxis[0].setExtremes(xMin, xMax, true);
                                    chart4.xAxis[0].setExtremes(xMin, xMax, true);

                                    ///Make sure to set back to false... able to listen events
                                     chart2.options.chart.isZoomed = false;
                                     chart3.options.chart.isZoomed = false;
                                     chart4.options.chart.isZoomed = false;
                                    //alert( "Inside the event box...." + xMin + " " + xMax);                                    
                                }
                             }
                        }
              },*/
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
                  text :" Portfolio Performance",
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

   var chart2 = new Highcharts.StockChart({
     chart: {
                        renderTo: $('#port_container2')[0]
                      },
              /*xAxis: {
                events: {
                             afterSetExtremes: function() {
                              //alert( "Inside the event box....");
                              if (!this.chart.options.chart.isZoomed) {
                                    var xMin = this.chart.xAxis[0].min;
                                    var xMax = this.chart.xAxis[0].max;
                                   
                                   ///Make sure to avoid recursive loop set them to true...
                                     chart2.options.chart.isZoomed = true;
                                     chart3.options.chart.isZoomed = true;
                                     chart4.options.chart.isZoomed = true;

                                    chart2.xAxis[0].setExtremes(xMin, xMax, true);
                                    chart3.xAxis[0].setExtremes(xMin, xMax, true);
                                    chart4.xAxis[0].setExtremes(xMin, xMax, true);

                                    ///Make sure to set back to false... able to listen events
                                     chart2.options.chart.isZoomed = false;
                                     chart3.options.chart.isZoomed = false;
                                     chart4.options.chart.isZoomed = false;
                                    //alert( "Inside the event box...." + xMin + " " + xMax);                                    
                                }
                             }
                        }
              },*/
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
                  text :" Portfolio Cumulative Returns",
                  floating: true,
                  align: 'left',
                  x: 75,
                  y: 70
              },
              series : [{
                  name : dataList[2].name,
                  data : dataList[2].data,
                  turboThreshold: 0, ///Speed up and make sure it supports more points
                  tooltip: {
                      valueDecimals: 2
                  },
                  id : 'dataseries'
             }]
         });

  }

  $('#indicatorList').on('click', '#dLabel', function(){
    console.log("inside dLabel")
    $('#showList').empty()
    $('#showList').html('<li><a href="#" id="indicator-1">BBands</a>'
                         +'</li><li><a href="#" id="indicator-1">SMA-20</a></li>'
                         +'</li><li><a href="#" id="indicator-1">EMA-10</a></li>'
                        );
  });

  $('#indicatorList').on('click','#indicator-1',function(){
      var stkticker = $('input.typeahead.tt-input').val();
      var drp = $('#reportrange2').data('daterangepicker');
      var indicator = $(this).text();
      $.ajax({
              url: '/strategies/backtest_indicators/?Ticker='+stkticker+'&indicator='+indicator+"&stdate="+drp.startDate.toISOString()+"&enddate="+drp.endDate.toISOString(),
              type: 'GET',
              async: true,
              dataType: "json",
              beforeSend: function( xhr, status ) {
               //alert( "Before calling function" + stkticker);
               //Indicates progress bar...
               $("*").css("cursor", "progress");
              }, 
              success: function (data) {
                console.log("Inside Success")
                if (indicator == "BBands")
                {
                  bbseries = []
                  bbseries[0] = {name: "price", data: data.price};
                  bbseries[1] = {name: "upper", data: data.upper};
                  bbseries[2] = {name: "middle", data: data.middle};
                  bbseries[3] = {name: "lower", data: data.lower};
                  bbseries[4] = {name: "ema_10", data: data.ema_10};
                  bbseries[5] = {name: "stop-loss", data: data.orders};
                  bbseries[6] = {name: "entry-exit", data: data.resultdata};
                  displayIndicatorData(bbseries,stkticker);
                }
                if (indicator == "SMA-20")
                {
                  smaseries = []
                  smaseries[0] = {name: "price", data: data.price};
                  smaseries[1] = {name: "sma-20", data: data.sma_20};
                  smaseries[2] = {name: "stop-loss", data: data.orders};
                  smaseries[3] = {name: "entry-exit", data: data.resultdata};
                  displaySMAData(smaseries,stkticker);
                }
                if (indicator == "EMA-10")
                {
                  emaseries = []
                  emaseries[0] = {name: "price", data: data.price};
                  emaseries[1] = {name: "ema-10", data: data.ema_10};
                  displayEMA10Data(emaseries,stkticker);
                }

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


function displaySMAData (dataList, ticker) {
      var chartIndicator = new Highcharts.StockChart({
             chart: {
                        renderTo: $('#container')[0]
              },
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
                  text : ticker + ": SMA-20",
                  floating: true,
                  align: 'left',
                  x: 75,
                  y: 70
              },
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
                color: '#c62104',
                name : dataList[2].name,
                data : dataList[2].data,
                lineWidth : 0,
                marker : {
                    enabled : true,
                    radius : 5
                },
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries3'
               },{
                color: '#00cc00',
                name : dataList[3].name,
                data : dataList[3].data,
                lineWidth : 0,
                marker : {
                    enabled : true,
                    radius : 5
                },
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries4'
               }]
            });
    }


function displayEMA10Data (dataList, ticker) {
      var chartIndicator = new Highcharts.StockChart({
             chart: {
                        renderTo: $('#container')[0]
              },
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
                  text : ticker + ": EMA-10",
                  floating: true,
                  align: 'left',
                  x: 75,
                  y: 70
              },
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
               }]
            });
    }

function displayIndicatorData (dataList, ticker) {
      var chartIndicator = new Highcharts.StockChart({
             chart: {
                        renderTo: $('#container')[0]
              },
             /*xAxis: {
                events: {
                             afterSetExtremes: function() {
                              //alert( "Inside the event box....");
                              if (!this.chart.options.chart.isZoomed) {
                                    var xMin = this.chart.xAxis[0].min;
                                    var xMax = this.chart.xAxis[0].max;
                                    
                                     chart2.options.chart.isZoomed = true;
                                     chart1.options.chart.isZoomed = true;
                                     chart4.options.chart.isZoomed = true;

                                    chart2.xAxis[0].setExtremes(xMin, xMax, true);
                                    chart1.xAxis[0].setExtremes(xMin, xMax, true);
                                    chart4.xAxis[0].setExtremes(xMin, xMax, true);
                                    //alert( "Inside the event box...." + xMin + " " + xMax); 

                                     chart2.options.chart.isZoomed = false;
                                     chart1.options.chart.isZoomed = false;
                                     chart4.options.chart.isZoomed = false;                                   
                                }
                             }
                        }
             },*/

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
                  text : ticker + ": Bollinger Bands",
                  floating: true,
                  align: 'left',
                  x: 75,
                  y: 70
              },

               /*yAxis: [ { //--- primary yAxis
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
              }],*/

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
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries4'
               },{
                color: '#663399',
                name : dataList[4].name,
                data : dataList[4].data,
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries5'
               },{
                color: '#c62104',
                name : dataList[5].name,
                data : dataList[5].data,
                lineWidth : 0,
                marker : {
                    enabled : true,
                    radius : 5
                },
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries6'
               },{
                color: '#00cc00',
                name : dataList[6].name,
                data : dataList[6].data,
                lineWidth : 0,
                marker : {
                    enabled : true,
                    radius : 5
                },
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries7'
               }]
            });
    }


  
  
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
      var strategy = $(this).text();
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

  
  var options = {
            $DragOrientation: 0, /// This is too make sure drag even does not trigger slide show...
            $ArrowNavigatorOptions: {
                $Class: $JssorArrowNavigator$,
                $ChanceToShow: 2
            }
  };
  var jssor_slider1 = new $JssorSlider$('slider1_container', options);

  var chart1;
  var chart2;
  var chart3
  var chart4;

  function displayPortfolioData (dataList, ticker) {
    insideChart1 = true;
    chart1 = new Highcharts.StockChart({
      //$('#container').highcharts('StockChart', {
              chart: {
                        renderTo: $('#container')[0]
                      },
              xAxis: {
                events: {
                             afterSetExtremes: function() {
                              //alert( "Inside the event box....");
                              if (!this.chart.options.chart.isZoomed) {
                                    var xMin = this.chart.xAxis[0].min;
                                    var xMax = this.chart.xAxis[0].max;
                                   
                                   ///Make sure to avoid recursive loop set them to true...
                                     chart2.options.chart.isZoomed = true;
                                     chart3.options.chart.isZoomed = true;
                                     chart4.options.chart.isZoomed = true;

                                    chart2.xAxis[0].setExtremes(xMin, xMax, true);
                                    chart3.xAxis[0].setExtremes(xMin, xMax, true);
                                    chart4.xAxis[0].setExtremes(xMin, xMax, true);

                                    ///Make sure to set back to false... able to listen events
                                     chart2.options.chart.isZoomed = false;
                                     chart3.options.chart.isZoomed = false;
                                     chart4.options.chart.isZoomed = false;
                                    //alert( "Inside the event box...." + xMin + " " + xMax);                                    
                                }
                             }
                        }
              },
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
    chart4 = new Highcharts.StockChart({
             chart: {
                        renderTo: $('#container4')[0]
              },
             xAxis: {
                events: {
                             afterSetExtremes: function() {
                              //alert( "Inside the event box....");
                              if (!this.chart.options.chart.isZoomed) {
                                    var xMin = this.chart.xAxis[0].min;
                                    var xMax = this.chart.xAxis[0].max;
                                  
                                     chart2.options.chart.isZoomed = true;
                                     chart3.options.chart.isZoomed = true;
                                     chart1.options.chart.isZoomed = true;

                                    chart2.xAxis[0].setExtremes(xMin, xMax, true);
                                    chart3.xAxis[0].setExtremes(xMin, xMax, true);
                                    chart1.xAxis[0].setExtremes(xMin, xMax, true);
                                    //alert( "Inside the event box...." + xMin + " " + xMax);

                                     chart2.options.chart.isZoomed = false;
                                     chart3.options.chart.isZoomed = false;
                                     chart1.options.chart.isZoomed = false;                                    
                                }
                             }
                        }
             },
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
      chart3 = new Highcharts.StockChart({
             chart: {
                        renderTo: $('#container3')[0]
              },
             xAxis: {
                events: {
                             afterSetExtremes: function() {
                              //alert( "Inside the event box....");
                              if (!this.chart.options.chart.isZoomed) {
                                    var xMin = this.chart.xAxis[0].min;
                                    var xMax = this.chart.xAxis[0].max;
                                    
                                     chart2.options.chart.isZoomed = true;
                                     chart1.options.chart.isZoomed = true;
                                     chart4.options.chart.isZoomed = true;

                                    chart2.xAxis[0].setExtremes(xMin, xMax, true);
                                    chart1.xAxis[0].setExtremes(xMin, xMax, true);
                                    chart4.xAxis[0].setExtremes(xMin, xMax, true);
                                    //alert( "Inside the event box...." + xMin + " " + xMax); 

                                     chart2.options.chart.isZoomed = false;
                                     chart1.options.chart.isZoomed = false;
                                     chart4.options.chart.isZoomed = false;                                   
                                }
                             }
                        }
             },

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
    chart2 = new Highcharts.StockChart({
             chart: {
                        renderTo: $('#container2')[0]
              },
              xAxis: {
                events: {
                             afterSetExtremes: function() {
                              //alert( "Inside the event box....");
                              if (!this.chart.options.chart.isZoomed) {
                                    var xMin = this.chart.xAxis[0].min;
                                    var xMax = this.chart.xAxis[0].max;
                                    //var zmRange = computeTickInterval(xMin, xMax);

                                     chart3.options.chart.isZoomed = true;
                                     chart1.options.chart.isZoomed = true;
                                     chart4.options.chart.isZoomed = true;

                                    chart3.xAxis[0].setExtremes(xMin, xMax, true);
                                    chart1.xAxis[0].setExtremes(xMin, xMax, true);
                                    chart4.xAxis[0].setExtremes(xMin, xMax, true);
                                    //alert( "Inside the event box...." + xMin + " " + xMax); 

                                     chart3.options.chart.isZoomed = false;
                                     chart1.options.chart.isZoomed = false;
                                     chart4.options.chart.isZoomed = false;                                   
                                }
                             }
                        }
              },
     
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
                      height: '20%',
                      opposite: true
              },{ //--- terinary yAxis
                       title : {
                          text : 'Volume'
                       },
                        min: 0,
                        top: '65%',
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
                color: '#0000FF',
                name : dataList[1].name,
                data : dataList[1].data,
                lineWidth: 4,
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries1'
               },{
                yAxis: 0,
                color: '#008000',
                name : dataList[2].name,
                data : dataList[2].data,
                lineWidth: 4,
                turboThreshold: 0, ///Speed up and make sure it supports more points
                tooltip: {
                    valueDecimals: 2
                },
                id : 'dataseries2'
               },{
                yAxis: 0,
                color: '#FF00FF',
                name : dataList[3].name,
                data : dataList[3].data,
                lineWidth: 4,
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
                 lineWidth: 4,
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