let numAdded = typeof newNum == 'undefined' ? 1 : newNum;
let max = 4;

$('#anotherImage').click(function () {
    if(numAdded < max){
        $('.gallaryList').append("<li><input class=\"gall\" name=\"gall_"  + (numAdded+1)+ "\" type=file ></li>");

    }
    numAdded++;

   
    
    

    
});