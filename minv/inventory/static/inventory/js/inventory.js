$(function() {
  $('button[role="clear-button"]').click(function() {
    $(this).parent(/* span */).parent(/* input-group */).find("input, select").val("");
  });

  $('a[data-page]').click(function() {
    $('input[name="page"]').val($(this).data("page"));
    $('form').submit();
  });
});