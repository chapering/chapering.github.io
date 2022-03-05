---
layout: archive
title: "Publications"
permalink: /pubs/
author_profile: true
---
<style type="text/css" rel="stylesheet">
    #bibbase_header a[onclick="groupby('downloads')"] { display: none; }

    #group_article div.bibbase_group i+span { display: none; }
          #group_inproceedings div.bibbase_group i+span { display: none; }
          #group_mastersthesis div.bibbase_group i+span { display: none; }
          #group_phdthesis div.bibbase_group i+span { display: none; }
          #group_techreport div.bibbase_group i+span { display: none; }
          #group_unpublished div.bibbase_group i+span { display: none; }
          #group_incollection div.bibbase_group i+span { display: none; }

          #group_article div.bibbase_group i:after { content: " Journal Articles" }
          #group_inproceedings div.bibbase_group i:after { content: " Conference Papers" }
          #group_mastersthesis div.bibbase_group i:after { content: " Master's Thesis" }
          #group_phdthesis div.bibbase_group i:after { content: " PhD Thesis" }
          #group_techreport div.bibbase_group i:after { content: " Technical Report" }
          #group_unpublished div.bibbase_group i:after { content: " Unpublished" }
          #group_incollection div.bibbase_group i:after { content: " In Collection" }
</style>
<!-- >.groupby_dropdown { display: none; } -->

<title>Publications - Haipeng Cai</title>
<script src="https://bibbase.org/show?bib=chapering.github.io/pubs/hcaipub.bib&jsonp=1&nocache=1&fullnames=1&commas=true&theme=dividers"></script>

{% if author.googlescholar %}
  You can also find my articles on <u><a href="{{author.googlescholar}}">my Google Scholar profile</a>.</u>
{% endif %}

{% include base_path %}

{% for post in site.publications reversed %}
  {% include archive-single.html %}
{% endfor %}

<script type="text/javascript">
var sc_project=10604826; 
var sc_invisible=1; 
var sc_security="10996eea"; 
var scJsHost = (("https:" == document.location.protocol) ?
"https://secure." : "http://www.");
document.write("<sc"+"ript type='text/javascript' src='" +
scJsHost+
"statcounter.com/counter/counter.js'></"+"script>");
</script>
<noscript><div class="statcounter"><a title="website
statistics" href="http://statcounter.com/free-web-stats/"
target="_blank"><img class="statcounter"
src="http://c.statcounter.com/10604826/0/10996eea/1/"
alt="website statistics"></a></div></noscript>