from os import path

import pytest

from imports.mappings import import_genome_proteome_mappings, import_aminoacid_mutation_refseq_mappings
from database_testing import DatabaseTest
from models import Protein
from models import Gene
from database import db
from database import bdb
from database import bdb_refseq
from genomic_mappings import make_snv_key
from miscellaneous import make_named_gz_file

# this is output of:
# `zcat data/200616/all_variants/playground/annot_1.txt.gz | head`,
# except the last line which is fake and has one wrong reference (p.A5Q)

raw_mappings = """\
V4	V6	V7	V8	V3
chr17	 19282215	t	a	MAPK7:NM_002749:exon2:c.T2A:p.M1K,MAPK7:NM_139033:exon2:c.T2A:p.M1K,MAPK7:NM_139034:exon2:c.T2A:p.M1K,
chr17	 19282216	g	a	MAPK7:NM_002749:exon2:c.G3A:p.M1I,MAPK7:NM_139033:exon2:c.G3A:p.M1I,MAPK7:NM_139034:exon2:c.G3A:p.M1I,
chr17	 19282217	g	a	MAPK7:NM_002749:exon2:c.G4A:p.A2T,MAPK7:NM_139033:exon2:c.G4A:p.A2T,MAPK7:NM_139034:exon2:c.G4A:p.A2T,
chr17	 19282218	c	a	MAPK7:NM_002749:exon2:c.C5A:p.A2D,MAPK7:NM_139033:exon2:c.C5A:p.A2D,MAPK7:NM_139034:exon2:c.C5A:p.A2D,
chr17	 19282220	g	a	MAPK7:NM_002749:exon2:c.G7A:p.E3K,MAPK7:NM_139033:exon2:c.G7A:p.E3K,MAPK7:NM_139034:exon2:c.G7A:p.E3K,
chr17	 19282223	c	a	MAPK7:NM_002749:exon2:c.C10A:p.P4T,MAPK7:NM_139033:exon2:c.C10A:p.P4T,MAPK7:NM_139034:exon2:c.C10A:p.P4T,
chr17	 19282224	c	a	MAPK7:NM_002749:exon2:c.C11A:p.P4H,MAPK7:NM_139033:exon2:c.C11A:p.P4H,MAPK7:NM_139034:exon2:c.C11A:p.P4H,
chr17	 19282226	c	a	MAPK7:NM_002749:exon2:c.C13A:p.L5M,MAPK7:NM_139033:exon2:c.C13A:p.L5M,MAPK7:NM_139034:exon2:c.C13A:p.L5M,
chr17	 19282227	t	a	MAPK7:NM_002749:exon2:c.T14A:p.L5Q,MAPK7:NM_139033:exon2:c.T14A:p.L5Q,MAPK7:NM_139034:exon2:c.T14A:p.L5Q,
chr17	 19282227	t	a	MAPK7:NM_002749:exon2:c.T14A:p.A5Q,MAPK7:NM_139033:exon2:c.T14A:p.L5Q,MAPK7:NM_139032:exon2:c.T14A:p.L5Q,
"""


def create_test_data():

    mappings_filename = make_named_gz_file(raw_mappings)

    # create proteins from first three data rows
    protein_data = [
        ('NM_002749', 'MAEPLKEEDGEDGSAEPPGPVKAEPAHTAASVAAKNLALLKARSFDVTFDVGDEYEIIETIGNGAYGVVSSARRRLTGQQVAIKKIPNAFDVVTNAKRTLRELKILKHFKHDNIIAIKDILRPTVPYGEFKSVYVVLDLMESDLHQIIHSSQPLTLEHVRYFLYQLLRGLKYMHSAQVIHRDLKPSNLLVNENCELKIGDFGMARGLCTSPAEHQYFMTEYVATRWYRAPELMLSLHEYTQAIDLWSVGCIFGEMLARRQLFPGKNYVHQLQLIMMVLGTPSPAVIQAVGAERVRAYIQSLPPRQPVPWETVYPGADRQALSLLGRMLRFEPSARISAAAALRHPFLAKYHDPDDEPDCAPPFDFAFDREALTRERIKEAIVAEIEDFHARREGIRQQIRFQPSLQPVASEPGCPDVEMPSPWAPSGDCAMESPPPAPPPCPGPAPDTIDLTLQPPPPVSEPAPPKKDGAISDNTKAALKAALLKSLRSRLRDGPSAPLEAPEPRKPVTAQERQREREEKRRRRQERAKEREKRRQERERKERGAGASGGPSTDPLAGLVLSDNDRSLLERWTRMARPAAPALTSVPAPAPAPTPTPTPVQPTSPPPGPVAQPTGPQPQSAGSTSGPVPQPACPPPGPAPHPTGPPGPIPVPAPPQIATSTSLLAAQSLVPPPGLPGSSTPGVLPYFPPGLPPPDAGGAPQSSMSESPDVNLVTQQLSKSQVEDPLPPVFSGTPKGSGAGYGVGFDLEEFLNQSFDMGVADGPQDGQADSASLSASLLADWLEGHGMNPADIESLQREIQMDSPMLLADLPDLQDP*'),
        ('NM_139033', 'MAEPLKEEDGEDGSAEPPGPVKAEPAHTAASVAAKNLALLKARSFDVTFDVGDEYEIIETIGNGAYGVVSSARRRLTGQQVAIKKIPNAFDVVTNAKRTLRELKILKHFKHDNIIAIKDILRPTVPYGEFKSVYVVLDLMESDLHQIIHSSQPLTLEHVRYFLYQLLRGLKYMHSAQVIHRDLKPSNLLVNENCELKIGDFGMARGLCTSPAEHQYFMTEYVATRWYRAPELMLSLHEYTQAIDLWSVGCIFGEMLARRQLFPGKNYVHQLQLIMMVLGTPSPAVIQAVGAERVRAYIQSLPPRQPVPWETVYPGADRQALSLLGRMLRFEPSARISAAAALRHPFLAKYHDPDDEPDCAPPFDFAFDREALTRERIKEAIVAEIEDFHARREGIRQQIRFQPSLQPVASEPGCPDVEMPSPWAPSGDCAMESPPPAPPPCPGPAPDTIDLTLQPPPPVSEPAPPKKDGAISDNTKAALKAALLKSLRSRLRDGPSAPLEAPEPRKPVTAQERQREREEKRRRRQERAKEREKRRQERERKERGAGASGGPSTDPLAGLVLSDNDRSLLERWTRMARPAAPALTSVPAPAPAPTPTPTPVQPTSPPPGPVAQPTGPQPQSAGSTSGPVPQPACPPPGPAPHPTGPPGPIPVPAPPQIATSTSLLAAQSLVPPPGLPGSSTPGVLPYFPPGLPPPDAGGAPQSSMSESPDVNLVTQQLSKSQVEDPLPPVFSGTPKGSGAGYGVGFDLEEFLNQSFDMGVADGPQDGQADSASLSASLLADWLEGHGMNPADIESLQREIQMDSPMLLADLPDLQDP*'),
        ('NM_139034', 'MAEPLKEEDGEDGSAEPPGPVKAEPAHTAASVAAKNLALLKARSFDVTFDVGDEYEIIETIGNGAYGVVSSARRRLTGQQVAIKKIPNAFDVVTNAKRTLRELKILKHFKHDNIIAIKDILRPTVPYGEFKSVYVVLDLMESDLHQIIHSSQPLTLEHVRYFLYQLLRGLKYMHSAQVIHRDLKPSNLLVNENCELKIGDFGMARGLCTSPAEHQYFMTEYVATRWYRAPELMLSLHEYTQAIDLWSVGCIFGEMLARRQLFPGKNYVHQLQLIMMVLGTPSPAVIQAVGAERVRAYIQSLPPRQPVPWETVYPGADRQALSLLGRMLRFEPSARISAAAALRHPFLAKYHDPDDEPDCAPPFDFAFDREALTRERIKEAIVAEIEDFHARREGIRQQIRFQPSLQPVASEPGCPDVEMPSPWAPSGDCAMESPPPAPPPCPGPAPDTIDLTLQPPPPVSEPAPPKKDGAISDNTKAALKAALLKSLRSRLRDGPSAPLEAPEPRKPVTAQERQREREEKRRRRQERAKEREKRRQERERKERGAGASGGPSTDPLAGLVLSDNDRSLLERWTRMARPAAPALTSVPAPAPAPTPTPTPVQPTSPPPGPVAQPTGPQPQSAGSTSGPVPQPACPPPGPAPHPTGPPGPIPVPAPPQIATSTSLLAAQSLVPPPGLPGSSTPGVLPYFPPGLPPPDAGGAPQSSMSESPDVNLVTQQLSKSQVEDPLPPVFSGTPKGSGAGYGVGFDLEEFLNQSFDMGVADGPQDGQADSASLSASLLADWLEGHGMNPADIESLQREIQMDSPMLLADLPDLQDP*'),
    ]

    gene = Gene(name='MAPK7')

    proteins = {
        refseq_nm: Protein(refseq=refseq_nm, sequence=sequence, gene=gene)
        for refseq_nm, sequence in protein_data
    }

    # we need to have proteins with id in session - hence commit
    db.session.add(gene)
    db.session.commit()

    return mappings_filename, gene, proteins


class TestImport(DatabaseTest):

    @pytest.mark.serial
    def test_genome_proteome_mappings(self):

        mappings_filename, gene, proteins = create_test_data()

        broken_sequences = import_genome_proteome_mappings(
            proteins,
            path.dirname(mappings_filename),
            path.basename(mappings_filename)
        )

        # in some cases it is needed to reload bdb after import
        bdb.reload()

        assert not bdb[make_snv_key('1', 19282216, 'G', 'A')]
        assert bdb[make_snv_key('17', 19282216, 'G', 'A')]

        assert set(broken_sequences.keys()) == {'NM_002749'}
        assert [('NM_002749', 'L', 'A', '5', 'Q')] in list(broken_sequences.values())

    @pytest.mark.serial
    def test_gene_mutation_mappings(self):

        mappings_filename, gene, proteins = create_test_data()

        import_aminoacid_mutation_refseq_mappings(
            proteins,
            path.dirname(mappings_filename),
            path.basename(mappings_filename)
        )

        # in some cases it is needed to reload bdb after import
        bdb_refseq.reload()

        assert bdb_refseq['MAPK7 M1K'] == set(protein.id for protein in proteins.values())
        retrieved_proteins = {Protein.query.get(protein_id) for protein_id in bdb_refseq['MAPK7 M1K']}
        assert retrieved_proteins == set(proteins.values())
