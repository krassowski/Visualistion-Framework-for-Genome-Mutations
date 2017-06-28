function init_tinymce(config)
{
    var default_config = {
        selector: 'textarea',
        body_class: 'page-content',
        content_css : [
            '/static/min/page.css',
            'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css'
        ],
        height: 260,
        browser_spellcheck: true,
        plugins : 'anchor advlist autolink link image lists charmap print preview fullscreen table imagetools textcolor colorpicker searchreplace code codesample autoresize',
        toolbar: 'undo redo | styleselect | bold italic | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | link image | codesample',
        table_default_attributes: {
            class: 'table table-bordered table-hover'
        },
        autoresize_max_height: 600,
        table_class_list: [
            {title: 'Default', value: 'table table-bordered table-hover'},
            {title: 'Hover, Striped', value: 'table table-bordered table-hover table-striped'},
            {title: 'Hover, Striped, without borders', value: 'table table-hover table-striped'},
            {title: 'Hover, without borders', value: 'table table-hover'},
            {title: 'Clear', value: 'table'}
        ],
        codesample_languages: [
            {text: 'HTML/XML', value: 'markup'},
            {text: 'JavaScript', value: 'javascript'},
            {text: 'CSS', value: 'css'},
            {text: 'Python', value: 'python'},
            {text: 'Bash', value: 'bash'},
        ]
    }

    update_object(default_config, config)

    tinymce.init(default_config)
}
