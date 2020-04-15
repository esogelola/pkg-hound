let numAdded = typeof newNum == 'undefined' ? 1 : newNum;
let max = 4;

$('#anotherImage').click(function () {
    if(numAdded < max){
        $('.gallaryList').append("<li>" +
        "<div class=\"input-group mb-3\">" +
                "<div class=\"input-group-prepend\">"+
                  "<span class=\"input-group-text\" id=\"gallFile\">Gallary #" + (numAdded+1)+ " </span>"+
                "</div>"+
                "<div class=\"custom-file\">"+
                  "<input  name=\"gall_"  + (numAdded+1)+ "\" type=file  class=\"gall custom-file-input\" id=\"inputGroupFile01\" aria-describedby=\"inputGroupFileAddon01\">"+
                  "<label class=\"custom-file-label\" for=\"inputGroupFile01\">Choose file</label>"+
                "</div>"+
              "</div></li>");
    }
    numAdded++;

    
    

    
});

$('#gallFile').on('change',function(){
    //get the file name
    var fileName = $(this).val();
    //replace the "Choose a file" label
    $(this).next('.custom-file-label').html(fileName);
    console.log(fileName)
})

$('body').on('change', 'li #inputGroupFile01', function() {
    var fileName = $(this).val();
    $(this).next('.custom-file-label').html(fileName);
});

