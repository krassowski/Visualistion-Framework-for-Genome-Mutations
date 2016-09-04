def check_semicolon_separated_data_redundancy(path):
    with open(path) as f:
        for line in f:
            data = line.split('\t')
            mutation_field_elements = data[9].split(';')
            assert len(set(mutation_field_elements)) == 1


def test_data_assertions():
    semicolon_issue_affected_files = [
        'data/mutations/TCGA_muts_annotated.txt',
        'data/mutations/clinvar_muts_annotated.txt',
        'data/mutations/ESP6500_muts_annotated.txt',
    ]

    for path in semicolon_issue_affected_files:
        check_semicolon_separated_data_redundancy(path)
