INJECT_INCLUDES_TEMPLATE = """
<script>
(function() {{
  var script_iframe = $("#{id}");

  var script_iframe_inject_function = function() {{
    var cw = script_iframe[0].contentWindow.document;
{injects}
  }};
  script_iframe.on("load", script_iframe_inject_function);
}})();
</script>
"""

SINGLE_INJECT_TEMPLATE = """
var new_{num} = cw.createElement("{type}");
    new_{num}.{type_type} = "{type_value}";
    new_{num}.{src_type} = "{addr}";
    new_{num}.id = "id-{name}";
    cw.getElementsByTagName("{where}")[0].appendChild(new_{num});
"""

INJECT_IMAGES_TEMPLATE = """
    var new_img_addresses = cw.createElement("script");
    new_img_addresses.innerHTML = '{img_addrs}';
    new_img_addresses.id = "id-img_addrs";
    cw.getElementsByTagName("{where}")[0].appendChild(new_img_addresses);
"""
