import gzip
from imports.mutations import MutationImportManager
from database_testing import DatabaseTest
from models import Protein
from models import TCGAMutation
from database import db
from miscellaneous import make_named_temp_file


muts_import_manager = MutationImportManager()


# this is output of `zcat data/mutations/TCGA_muts_annotated.txt.gz | head`
tcga_mutations = """\
Chr	Start	End	Ref	Alt	Func.refGene	Gene.refGene	GeneDetail.refGene	ExonicFunc.refGene	AAChange.refGene	V11
1	156647053	156647053	C	G	exonic	NES	.	nonsynonymous SNV	NES:NM_006617:exon1:c.G4C:p.E2Q	comments: Bladder Urothelial Carcinoma;TCGA-BL-A0C8-01A-11D-A10S-08;NES
1	161047356	161047356	G	A	exonic	PVRL4	.	nonsynonymous SNV	PVRL4:NM_030916:exon3:c.C617T:p.S206L	comments: Bladder Urothelial Carcinoma;TCGA-BL-A0C8-01A-11D-A10S-08;PVRL4
1	172558229	172558229	A	T	exonic	SUCO	.	nonsynonymous SNV	SUCO:NM_001282751:exon16:c.A299T:p.Q100L,SUCO:NM_016227:exon17:c.A2441T:p.Q814L,SUCO:NM_014283:exon18:c.A1988T:p.Q663L	comments: Bladder Urothelial Carcinoma;TCGA-BL-A0C8-01A-11D-A10S-08;SUCO
1	224492852	224492852	G	C	exonic	NVL	.	nonsynonymous SNV	NVL:NM_001243147:exon6:c.C359G:p.S120C,NVL:NM_206840:exon6:c.C314G:p.S105C,NVL:NM_002533:exon7:c.C632G:p.S211C	comments: Bladder Urothelial Carcinoma;TCGA-BL-A0C8-01A-11D-A10S-08;NVL
1	243471361	243471361	C	G	exonic	SDCCAG8	.	nonsynonymous SNV	SDCCAG8:NM_006642:exon8:c.C811G:p.L271V	comments: Bladder Urothelial Carcinoma;TCGA-BL-A0C8-01A-11D-A10S-08;SDCCAG8
1	248551039	248551039	G	A	exonic	OR2T6	.	nonsynonymous SNV	OR2T6:NM_001005471:exon1:c.G130A:p.V44I	comments: Bladder Urothelial Carcinoma;TCGA-BL-A0C8-01A-11D-A10S-08;OR2T6
1	40766912	40766912	C	G	exonic	COL9A2	.	nonsynonymous SNV	COL9A2:NM_001852:exon32:c.G2012C:p.G671A	comments: Bladder Urothelial Carcinoma;TCGA-BL-A0C8-01A-11D-A10S-08;COL9A2
1	44474107	44474107	G	A	exonic;exonic	SLC6A9	.	nonsynonymous SNV;nonsynonymous SNV	SLC6A9:NM_001261380:exon4:c.C520T:p.R174W,SLC6A9:NM_006934:exon4:c.C565T:p.R189W,SLC6A9:NM_001024845:exon5:c.C508T:p.R170W,SLC6A9:NM_201649:exon5:c.C727T:p.R243W;SLC6A9:NM_001261380:exon4:c.C520T:p.R174W,SLC6A9:NM_006934:exon4:c.C565T:p.R189W,SLC6A9:NM_001024845:exon5:c.C508T:p.R170W,SLC6A9:NM_201649:exon5:c.C727T:p.R243W	comments: Bladder Urothelial Carcinoma;TCGA-BL-A0C8-01A-11D-A10S-08;SLC6A9
1	54395807	54395807	G	A	exonic	HSPB11	.	nonsynonymous SNV	HSPB11:NM_016126:exon3:c.C110T:p.T37M	comments: Bladder Urothelial Carcinoma;TCGA-BL-A0C8-01A-11D-A10S-08;HSPB11
"""

# assuming that there was mistyped sample name for first mutation,
# here it is an updated file with one record: this one updated mutation
# also a new mutation (the same pos, C>T) has been found to be important
# and we want it to be added
tcga_mutations_updated = """\
Chr	Start	End	Ref	Alt	Func.refGene	Gene.refGene	GeneDetail.refGene	ExonicFunc.refGene	AAChange.refGene	V11
1	156647053	156647053	C	G	exonic	NES	.	nonsynonymous SNV	NES:NM_006617:exon1:c.G4C:p.E2Q	comments: Bladder Urothelial Carcinoma;TCGA-BL-A0C8-01A-11D-A10S-09;NES
1	156647053	156647053	C	T	exonic	NES	.	nonsynonymous SNV	NES:NM_006617:exon1:c.G4T:p.E2K	comments: Bladder Urothelial Carcinoma;TCGA-BL-A0C8-01A-11D-A10S-09;NES
"""

class TestImport(DatabaseTest):

    def test_tcga_import(self):

        muts_filename = make_named_temp_file(
            data=tcga_mutations.encode(),
            mode='wb',
            opener=gzip.open
        )

        update_filename = make_named_temp_file(
            data=tcga_mutations_updated.encode(),
            mode='wb',
            opener=gzip.open
        )

        # create proteins from first three data rows
        protein_data = [
            ('NM_001282751', 'MEPSTPDTPKESPIVQLVQEEEEEASPSTVTLLGSGEQEDESSPWFESETQIFCSELTTICCISSFSEYIYKWCSVRVALYRQRSRTALSKGKDYLVLAQPPLLLPAESVDVSVLQPLSGELENTNIEREAETVVLGDLSSSMHQDDLVNHTVDAVELEPSHSQTLSQSLLLDITPEINPLPKIEVSESVEYEAGHIPSPVIPQESSVEIDNETEQKSESFSSIEKPSITYETNKVNELMDNIIKEDVNSMQIFTKLSETIVPPINTATVPDNEDGEAKMNIADTAKQTLISVVDSSSLPEVKEEEQSPEDALLRGLQRTATDFYAELQNSTDLGYANGNLVHGSNQKESVFMRLNNRIKALEVNMSLSGRYLEELSQRYRKQMEEMQKAFNKTIVKLQNTSRIAEEQDQRQTEAIQLLQAQLTNMTQLVSNLSATVAELKREVSDRQSYLVISLVLCVVLGLMLCMQRCRNTSQFDGDYISKLPKSNQYPSPKRCFSSYDDMNLKRRTSFPLMRSKSLQLTGKEVDPNDLYIVEPLKFSPEKKKKRCKYKIEKIETIKPEEPLHPIANGDIKGRKPFTNQRDFSNMGEVYHSSYKGPPSEGSSETSSQSEESYFCGISACTSLCNGQSQKTKTEKRALKRRRSKVQDQGKLIKTLIQTKSGSLPSLHDIIKGNKEITVGTFGVTAVSGHI*'),
            ('NM_006617', 'MEGCMGEESFQMWELNRRLEAYLARVKALEEQNELLSAELGGLRAQSADTSWRAHADDELAALRALVDQRWREKHAAEVARDNLAEELEGVAGRCQQLRLARERTTEEVARNRRAVEAEKCARAWLSSQVAELERELEALRVAHEEERVGLNAQAACAPRCPAPPRGPPAPAPEVEELARRLGEAWRGAVRGYQERVAHMETSLGQARERLGRAVQGAREGRLELQQLQAERGGLLERRAALEQRLEGRWQERLRATEKFQLAVEALEQEKQGLQSQIAQVLEGRQQLAHLKMSLSLEVATYRTLLEAENSRLQTPGGGSKTSLSFQDPKLELQFPRTPEGRRLGSLLPVLSPTSLPSPLPATLETPVPAFLKNQEFLQARTPTLASTPIPPTPQAPSPAVDAEIRAQDAPLSLLQTQGGRKQAPEPLRAEARVAIPASVLPGPEEPGGQRQEASTGQSPEDHASLAPPLSPDHSSLEAKDGESGGSRVFSICRGEGEGQIWGLVEKETAIEGKVVSSLQQEIWEEEDLNRKEIQDSQVPLEKETLKSLGEEIQESLKTLENQSHETLERENQECPRSLEEDLETLKSLEKENKELLKDVEVVRPLEKEAVGQLKPTGKEDTQTLQSLQKENQELMKSLEGNLETFLFPGTENQELVSSLQENLESLTALEKENQEPLRSPEVGDEEALRPLTKENQEPLRSLEDENKEAFRSLEKENQEPLKTLEEEDQSIVRPLETENHKSLRSLEEQDQETLRTLEKETQQRRRSLGEQDQMTLRPPEKVDLEPLKSLDQEIARPLENENQEFLKSLKEESVEAVKSLETEILESLKSAGQENLETLKSPETQAPLWTPEEINQGAMNPLEKEIQEPLESVEVNQETFRLLEEENQESLRSLGAWNLENLRSPEEVDKESQRNLEEEENLGKGEYQESLRSLEEEGQELPQSADVQRWEDTVEKDQELAQESPPGMAGVENEDEAELNLREQDGFTGKEEVVEQGELNATEEVWIPGEGHPESPEPKEQRGLVEGASVKGGAEGLQDPEGQSQQVGAPGLQAPQGLPEAIEPLVEDDVAPGGDQASPEVMLGSEPAMGESAAGAEPGPGQGVGGLGDPGHLTREEVMEPPLEEESLEAKRVQGLEGPRKDLEEAGGLGTEFSELPGKSRDPWEPPREGREESEAEAPRGAEEAFPAETLGHTGSDAPSPWPLGSEEAEEDVPPVLVSPSPTYTPILEDAPGPQPQAEGSQEASWGVQGRAEALGKVESEQEELGSGEIPEGPQEEGEESREESEEDELGETLPDSTPLGFYLRSPTSPRWDPTGEQRPPPQGETGKEGWDPAVLASEGLEAPPSEKEEGEEGEEECGRDSDLSEEFEDLGTEAPFLPGVPGEVAEPLGQVPQLLLDPAAWDRDGESDGFADEEESGEEGEEDQEEGREPGAGRWGPGSSVGSLQALSSSQRGEFLESDSVSVSVPWDDSLRGAVAGAPKTALETESQDSAEPSGSEEESDPVSLEREDKVPGPLEIPSGMEDAGPGADIIGVNGQGPNLEGKSQHVNGGVMNGLEQSEEVGQGMPLVSEGDRGSPFQEEEGSALKTSWAGAPVHLGQGQFLKFTQREGDRESWSSGED*'),
            ('NM_014283', 'MKKHRRALALVSCLFLCSLVWLPSWRVCCKESSSASASSYYSQDDNCALENEDVQFQKKDEREGPINAESLGKSGSNLPISPKEHKLKDDSIVDVQNTESKKLSPPVVETLPTVDLHEESSNAVVDSETVENISSSSTSEITPISKLDEIEKSGTIPIAKPSETEQSETDCDVGEALDASAPIEQPSFVSPPDSLVGQHIENVSSSHGKGKITKSEFESKVSASEQGGGDPKSALNASDNLKNESSDYTKPGDIDPTSVASPKDPEDIPTFDEWKKKVMEVEKEKSQSMHASSNGGSHATKKVQKNRNNYASVECGAKILAANPEAKSTSAILIENMDLYMLNPCSTKIWFVIELCEPIQVKQLDIANYELFSSTPKDFLVSISDRYPTNKWIKLGTFHGRDERNVQSFPLDEQMYAKYVKMFIKYIKVELLSHFGSEHFCPLSLIRVFGTSMVEEYEEIADSQYHSERQELFDEDYDYPLDYNTGEDKSSKNLLGSATNAILNMVNIAANILGAKTEDLTEGNKSISENATATAAPKMPESTPVSTPVPSPEYVTTEVHTHDMEPSTPDTPKESPIVQLVQEEEEEASPSTVTLLGSGEQEDESSPWFESETQIFCSELTTICCISSFSEYIYKWCSVRVALYRQRSRTALSKGKDYLVLAQPPLLLPAESVDVSVLQPLSGELENTNIEREAETVVLGDLSSSMHQDDLVNHTVDAVELEPSHSQTLSQSLLLDITPEINPLPKIEVSESVEYEAGHIPSPVIPQESSVEIDNETEQKSESFSSIEKPSITYETNKVNELMDNIIKEDVNSMQIFTKLSETIVPPINTATVPDNEDGEAKMNIADTAKQTLISVVDSSSLPEVKEEEQSPEDALLRGLQRTATDFYAELQNSTDLGYANGNLVHGSNQKESVFMRLNNRIKALEVNMSLSGRYLEELSQRYRKQMEEMQKAFNKTIVKLQNTSRIAEEQDQRQTEAIQLLQAQLTNMTQLVSNLSATVAELKREVSDRQSYLVISLVLCVVLGLMLCMQRCRNTSQFDGDYISKLPKSNQYPSPKRCFSSYDDMNLKRRTSFPLMRSKSLQLTGKEVDPNDLYIVEPLKFSPEKKKKRCKYKIEKIETIKPEEPLHPIANGDIKGRKPFTNQRDFSNMGEVYHSSYKGPPSEGSSETSSQSEESYFCGISACTSLCNGQSQKTKTEKRALKRRRSKVQDQGKLIKTLIQTKSGSLPSLHDIIKGNKEITVGTFGVTAVSGHI*'),
            ('NM_016227', 'MRGFLARPFLSTNQHLAQWGSPLPQGKGLVQLPSQHTRHSRPFHELCSKEENSATVPKLISLVVSSETIDFSNKTMDSRRDWEREKRILEGKLQLPKALARTQRARDEGRAWTSRWLQRRRSPESCEAPLSAPLWGPQRGLPGREPLRSRSASAIALRTIGHILALLLRLLHLGLGSGGCREDVPPSGRGKKEEKMKKHRRALALVSCLFLCSLVWLPSWRVCCKESSSASASSYYSQDDNCALENEDVQFQKKNTESKKLSPPVVETLPTVDLHEESSNAVVDSETVENISSSSTSEITPISKLDEIEKSGTIPIAKPSETEQSETDCDVGEALDASAPIEQPSFVSPPDSLVGQHIENVSSSHGKGKITKSEFESKVSASEQGGGDPKSALNASDNLKNESSDYTKPGDIDPTSVASPKDPEDIPTFDEWKKKVMEVEKEKSQSMHASSNGGSHATKKVQKNRNNYASVECGAKILAANPEAKSTSAILIENMDLYMLNPCSTKIWFVIELCEPIQVKQLDIANYELFSSTPKDFLVSISDRYPTNKWIKLGTFHGRDERNVQSFPLDEQMYAKYVKVELLSHFGSEHFCPLSLIRVFGTSMVEEYEEIADSQYHSERQELFDEDYDYPLDYNTGEDKSSKNLLGSATNAILNMVNIAANILGAKTEDLTEGNKSISENATATAAPKMPESTPVSTPVPSPEYVTTEVHTHDMEPSTPDTPKESPIVQLVQEEEEEASPSTVTLLGSGEQEDESSPWFESETQIFCSELTTICCISSFSEYIYKWCSVRVALYRQRSRTALSKGKDYLVLAQPPLLLPAESVDVSVLQPLSGELENTNIEREAETVVLGDLSSSMHQDDLVNHTVDAVELEPSHSQTLSQSLLLDITPEINPLPKIEVSESVEYEAGHIPSPVIPQESSVEIDNETEQKSESFSSIEKPSITYETNKVNELMDNIIKEDVNSMQIFTKLSETIVPPINTATVPDNEDGEAKMNIADTAKQTLISVVDSSSLPEVKEEEQSPEDALLRGLQRTATDFYAELQNSTDLGYANGNLVHGSNQKESVFMRLNNRIKALEVNMSLSGRYLEELSQRYRKQMEEMQKAFNKTIVKLQNTSRIAEEQDQRQTEAIQLLQAQLTNMTQLVSNLSATVAELKREVSDRQSYLVISLVLCVVLGLMLCMQRCRNTSQFDGDYISKLPKSNQYPSPKRCFSSYDDMNLKRRTSFPLMRSKSLQLTGKEVDPNDLYIVEPLKFSPEKKKKRCKYKIEKIETIKPEEPLHPIANGDIKGRKPFTNQRDFSNMGEVYHSSYKGPPSEGSSETSSQSEESYFCGISACTSLCNGQSQKTKTEKRALKRRRSKVQDQGKLIKTLIQTKSGSLPSLHDIIKGNKEITVGTFGVTAVSGHI*'),
            ('NM_030916', 'MPLSLGAEMWGPEAWLLLLLLLASFTGRCPAGELETSDVVTVVLGQDAKLPCFYRGDSGEQVGQVAWARVDAGEGAQELALLHSKYGLHVSPAYEGRVEQPPPPRNPLDGSVLLRNAVQADEGEYECRVSTFPAGSFQARLRLRVLVPPLPSLNPGPALEEGQGLTLAASCTAEGSPAPSVTWDTEVKGTTSSRSFKHSRSAAVTSEFHLVPSRSMNGQPLTCVVSHPGLLQDQRITHILHVSFLAEASVRGLEDQNLWHIGREGAMLKCLSEGQPPPSYNWTRLDGPLPSGVRVDGDTLGFPPLTTEHSGIYVCHVSNEFSSRDSQVTVDVLDPQEDSGKQVDLVSASVVVVGVIAALLFCLLVVVVVLMSRYHRRKAQQMTQKYEEELTLTRENSIRRLHSHHTDPRSQPEESVGLRAEGHPDSLKDNSSCSVMSEEPEGRSYSTLTTVREIETQTELLSPGSGRAEEEEDQDEGIKQAMNHFVQENGTLRAKPTGNGIYINGRGHLV*')
        ]

        proteins = {
            refseq_nm: Protein(refseq=refseq_nm, sequence=sequence)
            for refseq_nm, sequence in protein_data
        }

        with self.app.app_context():
            source_name = 'tcga'
            # let's pretend that we already have some proteins in our db
            db.session.add_all(proteins.values())

            muts_import_manager.perform(
                'load', proteins, [source_name], {source_name: muts_filename}
            )

            cancer_mutations = TCGAMutation.query.all()
            assert len(cancer_mutations) == 5

            first_row_mutation = proteins['NM_006617'].mutations[0]
            assert first_row_mutation.position == 2
            assert first_row_mutation.alt == 'Q'

            tcga_mutation = first_row_mutation.meta_TCGA[0]
            assert tcga_mutation.samples == 'TCGA-BL-A0C8-01A-11D-A10S-08'

            muts_import_manager.perform(
                'update', proteins, [source_name], {source_name: update_filename}
            )

            # updated correctly?
            assert tcga_mutation.samples == 'TCGA-BL-A0C8-01A-11D-A10S-09'

            # added correctly during update?
            assert len(list(proteins['NM_006617'].mutations)) == 2
            # select the new mutation:
            new_mutation = None
            for mutation in proteins['NM_006617'].mutations:
                if mutation != tcga_mutation:
                    new_mutation = mutation
            assert new_mutation
            # check correctness:
            assert new_mutation.position == 2
            assert new_mutation.alt == 'K'
            new_tcga_mutation = first_row_mutation.meta_TCGA[0]
            assert new_tcga_mutation.samples == 'TCGA-BL-A0C8-01A-11D-A10S-09'


tss_cancer_map_text = """\
A1	Breast invasive carcinoma
A2	Breast invasive carcinoma
A3	Kidney renal cell carcinoma
"""


def test_tss_cancer_map():
    from imports.mutations.mc3 import load_tss_cancer_map

    tss_filename = make_named_temp_file(
        data=tss_cancer_map_text
    )

    tss_map = load_tss_cancer_map(tss_filename)

    assert type(tss_map) is dict
    assert tss_map['A1'] == 'Breast invasive carcinoma'
    assert tss_map['A3'] == 'Kidney renal cell carcinoma'
