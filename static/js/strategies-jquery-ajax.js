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
    });


}); //end of ready function