import flask
from flask import render_template as template
from flask import jsonify
from flask import request
from flask_classful import FlaskView
from flask_classful import route
from sqlalchemy.sql.elements import TextClause

from models import Protein, Cancer, InheritedMutation, Disease, ClinicalData, source_manager, SiteType, MC3Mutation
from models import Mutation
from models import Gene
from models import Site
from models import GeneList
from models import GeneListEntry
from sqlalchemy import func, text
from sqlalchemy import distinct
from sqlalchemy import case
from sqlalchemy import literal_column
from database import db
from helpers.views import AjaxTableView
from helpers.filters.manager import joined_query, FilterManager
from helpers.filters import Filter
from helpers.widgets import FilterWidget
from .filters import sqlalchemy_filter_from_source_name, create_dataset_labels, source_dependent_filters, \
    create_dataset_specific_widgets

from sqlalchemy import and_
import sqlalchemy


def select_textual_filters(filters):
    return [
        filter_ for filter_ in filters
        if type(filter_) is TextClause
    ]


def select_filters(filters, models):
    """Selects filters which are applicable to at least one of given models."""
    selected = set()
    tables = [model.__table__ for model in models]

    table_containing_types = [
        sqlalchemy.sql.schema.Column,
        sqlalchemy.sql.annotation.AnnotatedColumn
    ]

    for filter_ in filters:
        stack = list(filter_.get_children())
        for entity in stack:
            if type(entity) in table_containing_types:
                if entity.table in tables:
                    selected.add(filter_)
            if isinstance(entity, sqlalchemy.sql.selectable.Selectable):
                stack.extend(entity.get_children())
    return selected


def chain_filters(filters, conjunction=and_):
    if len(filters) == 1:
        return next(iter(filters))
    return conjunction(*filters)


def prepare_subqueries(sql_filters, required_joins):
    """Return three sub-queries suitable for use in protein queries which are:
        - mutations count (muts_cnt),
        - PTM mutations count (ptm_muts_cnt),
        - sites count (ptm_sites_cnt)

    Returned sub-queries are labelled as shown in parentheses above.
    """

    muts_filtering_models = [Mutation, MC3Mutation, InheritedMutation, ClinicalData, Disease, Cancer]

    any_site_filters = select_filters(sql_filters, [Site, SiteType])
    any_muts_filters = select_filters(sql_filters, muts_filtering_models)

    muts = (
        joined_query(
            (
                db.session.query(func.count(Mutation.id))
                .filter(Mutation.protein_id == Protein.id)
            ),
            required_joins,
            limit_to=muts_filtering_models
        )
        .filter(and_(*any_muts_filters))
    )

    sites = (
        db.session.query(func.count(Site.id))
        .filter(Site.protein_id == Protein.id)
    )

    if any_site_filters:
        ptm_muts = (
            db.session.query(
                func.count(distinct(case(
                    [
                        (
                            (
                                Site.position.between(
                                    Mutation.position - 7,
                                    Mutation.position + 7
                                )
                            ),
                            Mutation.id
                        )
                    ],
                    else_=literal_column('NULL')
                )))
            )
            .filter(and_(
                Mutation.protein_id == Protein.id,
                Mutation.precomputed_is_ptm
            ))
            .join(Site, Site.protein_id == Mutation.protein_id)
            .join(SiteType, Site.types)
            .filter(chain_filters(any_site_filters))
        )

        ptm_muts = (
            joined_query(ptm_muts, required_joins, limit_to=muts_filtering_models)
            .filter(chain_filters(any_muts_filters))
        )
        sites = (
            sites
            .join(SiteType, Site.types)
            .filter(chain_filters(any_site_filters))
        )
    else:
        ptm_muts = (
            db.session.query(func.count(Mutation.id))
            .filter(and_(
                Mutation.protein_id == Protein.id,
                Mutation.precomputed_is_ptm
            ))
        )
        ptm_muts = (
            joined_query(ptm_muts, required_joins, limit_to=muts_filtering_models)
            .filter(chain_filters(any_muts_filters))
        )

    # if no specific dataset is chosen
    # (so if we do not have guarantee that the muts chosen are confirmed)
    if not any_muts_filters:
        muts = muts.filter(Mutation.is_confirmed == True)
        ptm_muts = ptm_muts.filter(Mutation.is_confirmed == True)

    muts = muts.label('muts_cnt')
    ptm_muts = ptm_muts.label('ptm_muts_cnt')
    sites = sites.label('ptm_sites_cnt')

    return muts, ptm_muts, sites


class GeneViewFilters(FilterManager):

    def __init__(self, **kwargs):

        filters = [
            Filter(
                Mutation, 'sources', comparators=['in'],
                choices=list(source_manager.visible_fields.keys()),
                default=None, nullable=True,
                as_sqlalchemy=sqlalchemy_filter_from_source_name
            ),
            Filter(
                Site, 'types', comparators=['in'],
                choices={
                    site_type.name: site_type
                    for site_type in SiteType.available_types()
                },
                as_sqlalchemy=SiteType.fuzzy_filter,
                as_sqlalchemy_joins=[SiteType]
            ),
            Filter(
                Gene, 'has_ptm_muts',
                comparators=['eq'],
                as_sqlalchemy=lambda value: text('ptm_muts_cnt > 0') if value else text('true')
            ),
            Filter(
                Gene, 'is_known_kinase',
                comparators=['eq'],
                as_sqlalchemy=lambda value: Protein.kinase.any()
            )
        ] + [
            filter
            for filter in source_dependent_filters()
            if filter.has_sqlalchemy    # filters without sqlalchemy interface are not supported for table views
        ]
        super().__init__(filters)
        self.update_from_request(request)


def make_widgets(filter_manager, include_dataset_specific=False):
    base_widgets = {
        'dataset': FilterWidget(
            'Mutation dataset', 'radio',
            filter=filter_manager.filters['Mutation.sources'],
            labels=create_dataset_labels(),
            disabled_label='All datasets'
        ),
        'ptm_type': FilterWidget(
            'Type of PTM site', 'radio',
            filter=filter_manager.filters['Site.types'],
            disabled_label='all sites'
        ),
        'has_ptm': FilterWidget(
            'Genes with PTM mutations only', 'checkbox',
            filter=filter_manager.filters['Gene.has_ptm_muts'],
            disabled_label='all genes',
            labels=['Genes with PTM mutations only']
        ),
        'is_kinase': FilterWidget(
            'Genes of known kinases', 'checkbox',
            filter=filter_manager.filters['Gene.is_known_kinase'],
            labels=['Genes of known kinases only']
        ),
    }
    if include_dataset_specific:
        dataset_specific = create_dataset_specific_widgets(
            None,
            filter_manager.filters,
            population_widgets=False
        )
        base_widgets['dataset_specific'] = dataset_specific
    return base_widgets


def ajax_query(sql_filters, joins):

    muts, ptm_muts, sites = prepare_subqueries(sql_filters, joins)

    protein_filters = select_filters(sql_filters, [Protein])

    textutal_filters = select_textual_filters(sql_filters)
    query = (
        db.session.query(
            Gene.name,
            Gene.full_name,
            muts,
            ptm_muts,
            sites
        )
        .select_from(Gene)
        .join(Protein, Protein.id == Gene.preferred_isoform_id)
        .filter(*protein_filters)
        .group_by(Gene.id)
        .having(and_(*textutal_filters))
    )
    return query


def ajax_query_count(sql_filters, joins):

    muts, ptm_muts, sites = prepare_subqueries(sql_filters, joins)
    protein_filters = select_filters(sql_filters, [Protein])
    textutal_filters = select_textual_filters(sql_filters)

    select = [Gene.id]
    if textutal_filters:
        select.append(ptm_muts)

    query = (
        db.session.query(*select)
        .select_from(Gene)
        .join(Protein, Protein.id == Gene.preferred_isoform_id)
        .filter(*protein_filters)
        .group_by(Gene.id)
        .having(and_(*textutal_filters))
    )
    return query


class GeneView(FlaskView):

    def check_filters(self):
        from .filters import ProteinFiltersData
        filter_manager = self.filter_manager
        response = {
            'content': {},
            # diseases in dataset-specific widgets could limited to those of
            # mutations of genes matching filtering criteria - but it would
            # require another (expensive) filtering operation
            'filters': ProteinFiltersData(filter_manager, None).to_json()
        }

        return jsonify(response)

    def show(self, gene_name):
        gene = Gene.query.filter_by(name=gene_name).one()
        return template('gene/show.html', gene=gene)

    def before_request(self, name, *args, **kwargs):
        filter_manager = GeneViewFilters()
        endpoint = self.build_route_name(name)

        flask.g.filter_manager = filter_manager

        return filter_manager.reformat_request_url(
            request, endpoint, *args, **kwargs
        )

    @property
    def filter_manager(self):
        return flask.g.filter_manager

    def isoforms(self, gene_name):
        gene = Gene.query.filter_by(name=gene_name).one()
        return jsonify({
            'preferred': gene.preferred_isoform.to_json(),
            'alternative': [
                isoform.to_json()
                for isoform in gene.alternative_isoforms
            ]
        })

    def list(self, list_name):
        filter_manager = GeneViewFilters()
        widgets = make_widgets(filter_manager, True)
        return template(
            'gene/list.html', list_name=list_name,
            widgets=widgets, filter_manager=filter_manager
        )

    def lists(self):
        lists = GeneList.query.all()
        return template('gene/lists.html', lists=lists)

    def list_data(self, list_name):
        gene_list = GeneList.query.filter_by(name=list_name).first_or_404()

        def query_constructor(sql_filters, joins):
            muts, ptm_muts, sites = prepare_subqueries(sql_filters, joins)

            textutal_filters = select_textual_filters(sql_filters)
            textutal_filters.append(text('muts_cnt > 0'))
            protein_filters = select_filters(sql_filters, [Protein])

            return (
                db.session.query(
                    Gene.name,
                    Gene.full_name,
                    Protein.refseq,
                    muts,
                    ptm_muts,
                    sites,
                    GeneListEntry.fdr
                )
                .select_from(GeneListEntry)
                .filter(GeneListEntry.gene_list_id == gene_list.id)
                .join(Gene, Gene.id == GeneListEntry.gene_id)
                .join(Protein, Protein.id == Gene.preferred_isoform_id)
                .filter(*protein_filters)
                .group_by(Gene)
                .having(and_(*textutal_filters))
            )

        def count_query_constructor(sql_filters, joins):
            muts, ptm_muts, sites = prepare_subqueries(sql_filters, joins)

            textutal_filters = select_textual_filters(sql_filters)
            textutal_filters.append(text('muts_cnt > 0'))
            protein_filters = select_filters(sql_filters, [Protein])

            return (
                db.session.query(
                    GeneListEntry.id,
                    ptm_muts,
                    muts
                )
                .select_from(GeneListEntry)
                .join(Gene, GeneListEntry.gene_id == Gene.id)
                .join(Protein, Protein.id == Gene.preferred_isoform_id)
                .filter(*protein_filters)
                .filter(GeneListEntry.gene_list_id == gene_list.id)
                .group_by(GeneListEntry)
                .having(and_(*textutal_filters))
            )

        ajax_view = AjaxTableView.from_query(
            query=query_constructor,
            results_mapper=lambda row: row._asdict(),
            filters_class=GeneViewFilters,
            search_filter=lambda q: Gene.name.like(q + '%'),
            count_query=count_query_constructor,
            sort='fdr'
        )
        return ajax_view(self)

    def browse(self):
        filter_manager = GeneViewFilters()
        widgets = make_widgets(filter_manager)
        return template('gene/browse.html', widgets=widgets)

    browse_data = route('browse_data')(
        AjaxTableView.from_query(
            query=ajax_query,
            results_mapper=lambda row: row._asdict(),
            filters_class=GeneViewFilters,
            search_filter=lambda q: Gene.name.like(q + '%'),
            count_query=ajax_query_count,
            sort='name'
        )
    )
