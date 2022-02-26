---
layout: archive
#title: "Publications"
permalink: /pubs/
author_profile: true
---

<script src="https://bibbase.org/show?bib=chapering.github.io/pubs/hcaipub.bib&jsonp=1&nocache=1&fullnames=1&commas=true&theme=dividers"></script>

{% if author.googlescholar %}
  You can also find my articles on <u><a href="{{author.googlescholar}}">my Google Scholar profile</a>.</u>
{% endif %}

{% include base_path %}

{% for post in site.publications reversed %}
  {% include archive-single.html %}
{% endfor %}
