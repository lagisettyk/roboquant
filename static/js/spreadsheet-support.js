//// Handsontable spreadsheett related functionality purpose....
/*
document.addEventListener("DOMContentLoaded", function() {

    function getData() {
      return [
        ['', 'Kia', 'Nissan', 'Toyota', 'Honda', 'Mazda', 'Ford'],
        ['2012', 10, 11, 12, 13, 15, 16],
        ['2013', 10, 11, 12, 13, 15, 16],
        ['2014', 10, 11, 12, 13, 15, 16],
        ['2015', 10, 11, 12, 13, 15, 16],
        ['2016', 10, 11, 12, 13, 15, 16]
      ];
    }
    
    // Instead of creating a new Handsontable instance
    // with the container element passed as an argument,
    // you can simply call .handsontable method on a jQuery DOM object.
    var $container = $("#example1");
    
    $container.handsontable({
      data: getData(),
      rowHeaders: true,
      colHeaders: true,
      contextMenu: true
    });
    
    // This way, you can access Handsontable api methods by passing their names as an argument, e.g.:
    var hotInstance = $("#example1").handsontable('getInstance');
    
    function bindDumpButton() {
        if (typeof Handsontable === "undefined") {
          return;
        }
    
        Handsontable.Dom.addEvent(document.body, 'click', function (e) {
    
          var element = e.target || e.srcElement;
    
          if (element.nodeName == "BUTTON" && element.name == 'dump') {
            var name = element.getAttribute('data-dump');
            var instance = element.getAttribute('data-instance');
            var hot = window[instance];
            console.log('data of ' + name, hot.getData());
          }
        });
      }
    //bindDumpButton();

}); /// end of DOM Content Loaded event.....
*/


$(document).ready( function() {

  /// Functions related to handsontable .....
  function getData() {
      return [
        ['', 'Kia', 'Nissan', 'Toyota', 'Honda', 'Mazda', 'Ford'],
        ['2012', 10, 11, 12, 13, 15, 16],
        ['2013', 10, 11, 12, 13, 15, 16],
        ['2014', 10, 11, 12, 13, 15, 16],
        ['2015', 10, 11, 12, 13, 15, 16],
        ['2016', 10, 11, 12, 13, 15, 16]
      ];
    }
    
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

  ////block corrosponds too date-range picker....
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

}); //end of ready function