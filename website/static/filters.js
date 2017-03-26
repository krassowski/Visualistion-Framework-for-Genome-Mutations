/**
 * jQuery object
 * @external jQuery
 * @see {@link http://api.jquery.com/jQuery/}
 */

/**
 * Server response for filtering query for given representation.
 * @typedef {Object} ServerResponse
 * @property {FiltersData} filters
 * @property {RepresentationData} representation - Representation specific data.
 */

/**
 * Filter-specific metadata allowing to recognise if a response id up-to-date,
 * to update widgets if dataset has changed and so on.
 * @typedef {Object} FiltersData
 * @property {boolean} checksum - Semaphore-like checksum of filters handled
 * @property {html} dataset_specific_widgets - Widgets applicable only to selected dataset
 * @property {string} query - Value of query as to be used in 'filters={{value}}' URL query string.
 * @property {string} expanded_query - Like query but including default filters values.
 */

/**
 * @abstract
 * @typedef {Object} RepresentationData
 */

// TODO "all" button
// TODO "clear" button


var AsyncFiltersHandler = function()
{
    var config;
    var form;
    var old_filters_query;

    /**
     * Generate checksum string for given query string.
     * @param {string} query
     * @returns {string} checksum of given query string
     */
    function make_checksum(query)
    {
        return md5(query);
    }

    /**
     * Serialize a form into a GET-parameters list (for use in URLs),
     * additionally, a checksum parameter (md5) will be added.
     * @param {jQuery} $form - Form to be serialized.
     * @returns {string} Generated query string (parameters).
     */
    function serialize_form($form)
    {

        var filters_query = $form.serialize();
        var checksum = make_checksum(filters_query);

        filters_query += filters_query ? '&' : '?';

        filters_query += 'checksum=' + checksum;
        return filters_query
    }

    /**
     * Transform current URL (location.href) to include provided parameters.
     * @param {string} parameters - Query string to be included.
     * @returns {string} Current URL updated with provided filters query.
     */
    function make_query_url(parameters)
    {
        var location = window.location.href;
        var splitted = location.split('#');
        var hash = splitted.length > 0 ? splitted[1] : '';
        location = splitted[0].split('?')[0];

        if (parameters) {
            location += '?' + parameters;
        }

        if (hash) {
            location += '#' + hash;
        }
        return location;
    }

    /** Callback to update event which will be bound to the form. */
    function on_update(do_not_save)
    {
        var filters_query = serialize_form(form);

        apply(filters_query, do_not_save);
    }

    /**
     * Serialize as much as (easily) possible inside given DOM structure.
     * Generally used to compare two HTML fragments containing similar but not identical forms.
     * If for both fragments the function returns the same, then then values of inputs are identical.
     * @param {jQuery} $dom_fragment - Part of HTML document to serialize.
     * @returns {string} Query string from serialized inputs inside given DOM fragment.
     */
    function serialize_fragment($dom_fragment)
    {
        return $dom_fragment.find('input,select').serialize()
    }

    /**
     * @param {FiltersData} data
     * @returns {boolean} is response up to date?
     */
    function is_response_actual(data)
    {
        return make_checksum(form.serialize()) === data.checksum;
    }

    /**
     * Replace filters form with relevant (updated) content:
     * - set up dataset-specific widgets if dataset has changed
     *   (we do not want to filter by cancer type in ESP6500 dataset)
     * - correctly selected checkboxes / inputs
     *   (when restoring to the old state with History API,
     *   those has to be replaced accordingly to old state)
     * @param {FiltersData} data - server response defining current state
     * @param {boolean} from_future - Was the update called on "popstate" History API event?
     */
    function update_form_html(data, from_future)
    {
        var html = $.parseHTML(data.dataset_specific_widgets);

        if(from_future)
        {
            form.html(history.state.form);
        }

        var dataset_widgets = $('.dataset-specific');

        // do not replace if it's not needed - so expanded lists stay expanded
        if(serialize_fragment(dataset_widgets) !== serialize_fragment($(html)))
        {
            dataset_widgets.html(html)
        }
    }

    /**
     * Handle response from.
     * @param {ServerResponse} data - server response defining current state
     * @param {boolean} from_future - Was the update called on "popstate" History API event?
     */
    function load(data, from_future)
    {
        var filters_data = data.filters;

        if (!is_response_actual(filters_data) && !from_future)
        {
            console.log('Skipping not actual response');
            return
        }

        config.data_handler(data.representation, filters_data);

        update_form_html(filters_data, from_future);

        var filters_query = '';
        if(filters_data.query)
        {
            filters_query += 'filters=' + filters_data.query;
        }

        config.on_loading_end();

        history.replaceState(history.state, '', make_query_url(filters_query))
    }

    /**
     * Apply filters provided in query:
     *  - ask server for data for those filters,
     *  - change URL,
     *  - record changes with History API.
     * @param {string} filters_query - Query string as returned by {@link serialize_form}
     * @param {boolean} [do_not_save=false] - Should this modification be recorded in history?
     * @param {boolean} [from_future=false] - Was called on "popstate" History API event?
     */
    function apply(filters_query, do_not_save, from_future)
    {
        config.on_loading_start();
        var history_action;

        if (!do_not_save) {
            history_action = history.pushState;
        }
        else {
            history_action = history.replaceState;
        }

        print(filters_query)
        print(make_query_url(filters_query))
        var state = {filters_query: filters_query, form: form.html(), handler: 'filters'};
        history_action(state, '', make_query_url(filters_query));

        $.ajax({
            url: config.representation_url,
            type: 'GET',
            data: filters_query,
            success: function(data){ load(data, from_future) }
        });

        old_filters_query = filters_query;
    }

    /**
     * Configuration object for AsyncFiltersHandler.
     * @typedef {Object} Config
     * @property {jQuery} form
     * @property {function} data_handler
     * @property {function} on_loading_start
     * @property {function} on_loading_end
     * @property {string} representation_url
     */

    return {
        /**
         * Initialize AsyncFiltersHandler
         * @param {Config} new_config
         */
        init: function(new_config)
        {
            config = new_config;
            form = config.form;
            form.on(
                'change',
                'select, input',
                function() { on_update() }
            );
            old_filters_query = serialize_form(form);
            form.find('.save').hide()
        },
        load: load,
        apply: apply,
        on_update: on_update
    };
};
