SELECT
  {% if not count %}
    base.filename AS filename, 
    base.checksum__min AS checksum,
    base.annotations__count AS annotation_count,

    {% for location in locations %}
    l{{ location.pk }}.checksum AS l{{ location.pk }}c,
    {% endfor %}

    {% for location in locations %}
    l{{ location.pk }}.filename IS NOT NULL{% if not forloop.last %},{% endif %}
    {% endfor %}
  {% else %}
    COUNT(*) AS count
  {% endif %}
FROM
  (
    {{ base_query|safe }}
  ) AS base
{% for location in locations %}
LEFT JOIN
    (
      SELECT filename, checksum
      FROM inventory_record
      WHERE inventory_record.location_id = {{ location.pk }}
    ) AS l{{ location.pk }}
    ON base.filename = l{{ location.pk }}.filename
{% endfor %}
WHERE
{% for location in locations %}
    {% if not forloop.first %}OR {% endif %}
    l{{ location.pk }}.filename IS NULL
    OR l{{ location.pk }}.checksum != base.checksum__min
{% endfor %}
{% if limit %}
LIMIT {{ limit }}
{% endif %}
{% if offset %}
OFFSET {{ offset }}
{% endif %}