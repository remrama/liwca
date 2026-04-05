"""Sphinx extension that generates a dictionary catalogue table from CATALOGUE."""

from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx.application import Sphinx


class DictCatalogueDirective(Directive):
    """Directive ``.. dict-catalogue::`` that renders the dictionary catalogue.

    Outputs a summary table followed by a detail section per dictionary.
    """

    has_content = False
    required_arguments = 0
    optional_arguments = 0

    def _build_table(self, catalogue):
        """Build the summary table."""
        table = nodes.table()
        tgroup = nodes.tgroup(cols=3)
        table += tgroup
        for width in (15, 50, 35):
            tgroup += nodes.colspec(colwidth=width)

        # Header
        thead = nodes.thead()
        tgroup += thead
        header_row = nodes.row()
        thead += header_row
        for label in ("Name", "Description", "Source"):
            entry = nodes.entry()
            entry += nodes.paragraph(text=label)
            header_row += entry

        # Body
        tbody = nodes.tbody()
        tgroup += tbody
        for name in sorted(catalogue):
            info = catalogue[name]
            row = nodes.row()

            # Name — link to the detail section anchor
            entry = nodes.entry()
            ref = nodes.reference("", "", nodes.literal(text=name), refid=name)
            entry += nodes.paragraph("", "", ref)
            row += entry

            # Description
            entry = nodes.entry()
            entry += nodes.paragraph(text=info.description)
            row += entry

            # Source
            entry = nodes.entry()
            source_para = nodes.paragraph()
            source_ref = nodes.reference("", info.source_label, refuri=info.source_url)
            source_para += source_ref
            entry += source_para
            row += entry

            tbody += row

        return table

    def _build_detail_sections(self, catalogue):
        """Build a section per dictionary with detail, examples, and metadata."""
        sections = []
        for name in sorted(catalogue):
            info = catalogue[name]

            section = nodes.section(ids=[name])
            section += nodes.title(text=name)

            # Detail paragraph
            if info.detail:
                section += nodes.paragraph(text=info.detail)

            # Metadata field list
            field_list = nodes.field_list()

            field_node = nodes.field()
            field_node += nodes.field_name(text="Language")
            field_body = nodes.field_body()
            field_body += nodes.paragraph(text=info.language)
            field_node += field_body
            field_list += field_node

            section += field_list

            # Citations
            if info.citations:
                section += nodes.paragraph(
                    text="Please cite the following when using this dictionary:"
                )
                citation_list = nodes.enumerated_list()
                for cite in info.citations:
                    item = nodes.list_item()
                    item += nodes.paragraph(text=cite)
                    citation_list += item
                section += citation_list

            # Example terms
            if info.examples:
                section += nodes.paragraph(text="Example terms:")
                bullet_list = nodes.bullet_list()
                for term in info.examples:
                    item = nodes.list_item()
                    item += nodes.paragraph("", "", nodes.literal(text=term))
                    bullet_list += item
                section += bullet_list

            sections.append(section)
        return sections

    def run(self):
        from liwca._catalogue import CATALOGUE

        result = [self._build_table(CATALOGUE)]
        result.extend(self._build_detail_sections(CATALOGUE))
        return result


def setup(app: Sphinx):
    app.add_directive("dict-catalogue", DictCatalogueDirective)
    return {"version": "0.1", "parallel_read_safe": True}
