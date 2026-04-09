import pickle
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_FILE = '/Users/allenenriquez/Desktop/SystemA/token.pickle'
SPREADSHEET_ID = '1Upp2lhiTeRsybaBHEy5_6FTBLcCN5fJ8l-TjpyqrGUs'

def get_creds():
    with open(TOKEN_FILE, 'rb') as token:
        creds = pickle.load(token)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

def main():
    creds = get_creds()
    sheets = build('sheets', 'v4', credentials=creds)

    # Columns: Business Name | Owner Name | Phone | Email | Website | City | Service Areas | Rating | Reviews | Owner LinkedIn | Facebook Page | Notes
    rows = [
        ['Century Painting', 'Jack Jordan', '(704) 245-9409', '', 'centurypaintingnc.com', 'Charlotte, NC', 'Charlotte Metro', '5.0', '300+', '', '', 'Residential, Commercial, Epoxy, Deck, Pressure Washing'],
        ['Standard Painting and Maintenance', 'Luis Aguirre', '(980) 422-5654', '', 'standardpaintingcharlotte.com', 'Mint Hill, NC', 'Charlotte area', '5.0', '148', '', '', 'Residential, Commercial, Cabinet, Deck'],
        ['Ukie Painting', 'Vitalii Skochenko', '(980) 447-6311', '', 'ukiepainting.com', 'Charlotte, NC', 'Charlotte, Matthews, Mint Hill, Ballantyne', '5.0', '400+', '', '', 'Residential, Commercial, Cabinet'],
        ["SouthEnd Painting and Roofing", 'Todd Cahill', '(704) 522-0000', '', 'southendpainting.com', 'Charlotte, NC', 'Charlotte, NC', '4.1', '58', '', '', 'Residential, Commercial, Roofing, Epoxy'],
        ['Pride Painting Inc.', 'Bob Bass / Mike Palladino', '(704) 333-1696', '', 'pridepaintingcharlotte.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ["Glenny's Painting and Remodeling", 'Carlos A. Glenny', '(980) 322-5043', '', 'glennyspaintingandremodeling.com', 'Charlotte, NC', 'Charlotte area', '4.9', '139', '', '', 'Residential, Commercial'],
        ['Advance Painting Contractors', '', '(704) 529-8405', '', 'advancecontractorsnc.com', 'Charlotte, NC', 'Greater Charlotte', '5.0', '113', '', '', 'Residential, Commercial, Deck, Carpentry'],
        ['A&K Painting Company', '', '(855) 812-8003', '', 'akpainting.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Commercial, Industrial'],
        ['Charlotte Paint Co. LLC', '', '(704) 827-1391', '', 'charlottepaint.com', 'Mount Holly, NC', 'Charlotte area', '', '', '', '', 'Commercial, Industrial'],
        ['Mecklenburg Paint Company', 'Liz Etheredge', '(704) 588-3113', '', 'meckpaint.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Commercial, Industrial'],
        ['W. Sumter Cox Painting Contractors', '', '(704) 525-2835', '', 'sumtercox.com', 'Charlotte, NC', 'Charlotte area', '5.0', '32', '', '', 'Residential, Commercial, Specialty'],
        ['Valentine Painting & Decorating', 'James Valentine', '(704) 443-4000', '', 'valentinepainting.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential'],
        ['Treadaway & Sons Painting & Wallcovering', 'Ricky & Michael Treadaway', '(704) 332-6557', '', 'treadawaypainting.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial, Wallpaper'],
        ['Time to Paint Inc.', 'Al Parada', '(704) 342-4759', '', '', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['Fine Finishes Custom Painting', '', '(980) 291-7510', '', 'finefinishescustompainting.com', 'Charlotte, NC', 'Charlotte area', '4.9', '130', '', '', 'Residential, Commercial'],
        ['B&W Painting Co.', 'Wheeler Reese', '(704) 358-4981', '', '', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['All Star Painting Plus', 'Michael Hook', '(704) 458-3816', '', 'allstarpaintingclt.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['Action Painting Pros', 'Jennifer McEachern', '(980) 333-4970', '', 'actionpaintingnc.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['Brothers Painting JJ LLC', 'Julio Martinez', '(704) 837-9811', '', 'brotherspaintingnc.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['Eagles Brothers Painting', 'Carlos Garcia', '(704) 277-2875', '', 'eaglesbrotherspainting.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Cabinet, Deck'],
        ['Painting & Moore Inc.', '', '(704) 567-7781', '', 'paintingandmoore.com', 'Charlotte, NC', 'Charlotte area', '3.84', '35', '', '', 'Residential, Commercial'],
        ['Zelaya Jr Painting', '', '(704) 286-6866', '', 'zelaya-jr-painting.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ["Ronald's Painting & Home Improvement", '', '(704) 507-1972', '', 'ronaldspainting.com', 'Charlotte, NC', 'Charlotte area', '4.7', '91', '', '', 'Residential, Commercial'],
        ['Happy Homes Painting', '', '(704) 804-4513', '', 'happyhomespainting.net', 'Charlotte, NC', 'Charlotte area', '5.0', '31', '', '', 'Residential'],
        ["Sal's Quality Painting & Maintenance", 'Sal Ingiaimo', '(704) 264-5516', '', 'salsqualitypainting.com', 'Charlotte, NC', 'Charlotte area', '5.0', '13', '', '', 'Residential, Commercial, Industrial'],
        ['DeHaan Painting', 'Matt DeHaan', '(980) 224-3191', '', 'dehaanpaints.com', 'Charlotte, NC', 'Charlotte area', '4.9', '110', '', '', 'Residential'],
        ['Perfection Painting Pros', '', '(704) 200-4268', '', 'perfectionpaintingpros.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['Precision Painting LLC', 'Chris Bachner', '(704) 909-7809', '', 'paintwithprecision.com', 'Charlotte, NC', 'Charlotte area', '4.89', '73', '', '', 'Residential, Commercial'],
        ['GW Painting', 'Elias Genao', '', '', 'gwpaintingco.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential'],
        ['Metrolina Painting Contractors', 'Ronnie MacMillan', '(704) 960-0717', '', 'metrolinapainting.com', 'Charlotte, NC', 'Charlotte Metro', '', '', '', '', 'Residential, Commercial'],
        ['Anthony Meggs Painting LLC', 'Anthony Meggs', '(704) 946-5587', '', 'anthony-meggs-painting.com', 'Monroe, NC', 'Charlotte Metro', '4.9', '90', '', '', 'Residential, Commercial, Epoxy, Cabinet'],
        ['Paintline Painting Company', '', '(704) 819-7493', '', 'paintlinepaintingcompany.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['Charlotte Painting Company', '', '(704) 930-9973', '', 'charlottepaintingcompany.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['FM Painting', '', '(704) 919-8564', '', 'fmpaintingnc.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['M.A. Painting LLC', '', '(980) 395-0082', '', 'mapaintingnc.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['Shadow 1 Painting & Remodel', '', '(980) 414-8480', '', 'shadow1painting.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential'],
        ['Dubon Painting', '', '(704) 323-9530', '', 'dubonpainting.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['Allied Painting', 'Todd', '(704) 978-7770', '', 'alliedpaintingnc.com', 'Charlotte, NC', 'Charlotte area', '5.0', '40', '', '', 'Residential, Commercial, Cabinet'],
        ['A Touch of a Brush', 'Albert', '(980) 271-8603', '', 'touchofabrush.com', 'Charlotte, NC', 'Charlotte area', '4.9', '87', '', '', 'Residential, Commercial, Cabinet'],
        ['Craftwork', '', '(704) 380-9035', '', 'craftwork.com', 'Charlotte, NC', 'Charlotte area', '4.9', '342', '', '', 'Residential, Cabinet'],
        ['Paint EZ of Charlotte', 'Jennifer & Jorge De La Rosa', '(704) 839-2161', '', 'paintez.com/charlotte', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['Charlotte Paint Pros', '', '(704) 837-4635', '', 'charlottepaintpros.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Pressure Washing'],
        ['Charlotte Paint Squad', '', '(704) 292-4853', '', 'charlottepaintsquad.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential'],
        ['GJ Painting Services', '', '(704) 713-8146', '', 'gjpaintingservices.com', 'Charlotte, NC', 'Charlotte area', '5.0', '122', '', '', 'Residential'],
        ['Avid Painting & Home Remodeling', 'John Castano', '(704) 780-2005', '', 'avidpaintingllc.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['Avalos Painting LLC', 'Rafael Avalos', '(980) 729-4071', '', '', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['The AV Painting', 'Fabian & Maria', '(704) 807-7978', '', 'theavpainting.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Cabinet'],
        ['A Plus Painting Contractors', 'Hugo Ramirez', '(704) 531-4445', '', 'apluspaintingcontractors.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['Aybar Painting Inc.', '', '(704) 906-9341', '', 'aybarpainting.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['Carolina Pro Painting Inc.', '', '(704) 363-1289', '', '', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['First Painting Company', 'Jon & Wendy Montes', '(980) 319-0115', '', 'firstpaintingcompany.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['Stellar Painting Solutions LLC', 'Gregory & Gina Moore', '(704) 575-8657', '', 'stellarpaintingsolutions.com', 'Charlotte, NC', 'Charlotte area', '4.9', '173', '', '', 'Residential, Commercial'],
        ['Bravo Professional Contractors', 'Fred Heath', '(980) 272-8609', '', 'bravoprocontractors.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial, Industrial, Flooring'],
        ['Superior Painting Pros & Wall Covering', '', '(704) 327-8937', '', 'superior-painting-pros.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial, Wallpaper'],
        ['Active Painting Contractors', 'Alberto Rangel', '(704) 837-6810', '', '', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['Painting Specialties Inc.', 'Ronnie Prophet', '(704) 375-3197', '', '', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['Top Shelf Custom Painting', '', '(704) 626-8336', '', '', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential'],
        ['Rhino Shield of North Carolina', 'Daniel Hoey', '(704) 597-4141', '', 'rhinoshieldcarolina.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial (Exterior Coating)'],
        ['Paint Trinity', '', '(704) 703-9659', '', 'painttrinity1.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Drywall'],
        ['Carolina Brothers Painting & Drywall', '', '', '', 'carolinabrotherspainting.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial, Drywall'],
        ['JG Painting Pros Inc.', '', '(704) 657-4880', '', 'jgpaintingprosinc.com', 'Cornelius, NC', 'Cornelius, Huntersville', '', '', '', '', 'Residential, Commercial'],
        ['Pro Painting Charlotte', '', '(704) 936-0153', '', 'paintingcharlotte.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['Thompson Professional Painting Co.', '', '(704) 477-7129', '', 'thompsonpropainting.com', 'Charlotte, NC', 'Charlotte Metro', '', '', '', '', 'Residential, Commercial'],
        ['Interstate Painting Contractors', '', '(704) 363-1256', '', 'interstatepaintingonline.com', 'Matthews, NC', 'Charlotte Metro', '', '', '', '', 'Residential, Commercial, Industrial'],
        ['Chiodo Custom Painting Inc.', 'David Chiodo', '(704) 408-6619', '', 'chiodocustompainting.com', 'Matthews, NC', 'Matthews, Charlotte', '', '', '', '', 'Residential'],
        ['Charlotte Pro Painters', 'Adam Mashal', '(704) 313-8452', '', 'charlottepropainters.com', 'Matthews, NC', 'Charlotte Metro', '', '', '', '', 'Residential, Commercial'],
        ['Carolina Painting Company', '', '(704) 996-9005', '', 'carolinapaintingcompany.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ["Carolina's Painting & Carpentry Inc.", '', '(704) 622-4599', '', 'carolinaspaint.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['A&E Painting Company', '', '', '', 'aepaintingco.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['JNB Painting LLC', 'Jhanson Valverde', '(704) 569-4496', '', 'jnbpaintingllc.com', 'Charlotte, NC', 'Charlotte, Gastonia', '', '', '', '', 'Residential, Commercial'],
        ['Admiring Painting Services', '', '(704) 919-9678', '', 'admiringpaintnc.com', 'Charlotte, NC', 'Charlotte area', '5.0', '1', '', '', 'Residential'],
        ['The Painters Charlotte', 'Alan White', '', '', 'thepainterscharlotte.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential'],
        ['South Charlotte Painters', 'Renzo Alva', '', '', 'southcharlottepainters.com', 'Charlotte, NC', 'South Charlotte', '', '', '', '', 'Residential'],
        ['Hatch Homes', 'Bill Gayler', '(980) 355-2075', '', 'hatchyourhome.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential (Exterior), Siding'],
        ['New Old Remodeling', '', '(704) 253-4525', '', 'newoldremodeling.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential (Exterior), Roofing'],
        ['Premium Painters', '', '(704) 318-6969', '', 'premiumpainters.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential'],
        ["Porter's Pro Painting", '', '(704) 777-1223', '', 'porterspropainting.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['BWH Services', '', '(704) 451-5245', '', 'bwh-services.com', 'Charlotte, NC', 'Charlotte area', '2.5', '6', '', '', 'Residential, Commercial'],
        ['MeckRen', '', '(980) 207-9395', '', '', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Residential, Commercial'],
        ['Paint Pros Plus LLC', 'Rodney Morton', '(980) 439-0658', '', 'paintprosplus.net', 'Concord, NC', 'Concord, Harrisburg', '', '', '', '', 'Residential, Commercial, Cabinet'],
        ['Rivera Painting Corp.', '', '(704) 400-4269', '', 'jriverapaintingcorp.com', 'Concord, NC', 'Concord area', '', '', '', '', 'Residential, Commercial'],
        ['DJO Home Painting', '', '(980) 229-4575', '', 'djohomepainting.com', 'Concord, NC', 'Concord area', '', '', '', '', 'Residential, Commercial'],
        ['Done Right Painting Company', '', '(888) 687-3221', '', 'donerightpaintingco.com', 'Concord, NC', 'Concord area', '', '', '', '', 'Residential, Commercial'],
        ['Allburn Painting LLC', 'Colburn Peterson', '(980) 781-7421', '', 'allburnpainting.com', 'Concord, NC', 'Concord area', '', '', '', '', 'Residential, Commercial'],
        ['Pro Classic Painting', '', '(704) 241-5606', '', 'proclassicpainting.net', 'Gastonia, NC', 'Gastonia area', '', '', '', '', 'Residential, Commercial, Epoxy, Deck'],
        ['Straight Edge Painting Pros', 'Wes Reese', '(704) 870-7600', '', 'straightedgepaintingpros.com', 'Gastonia, NC', 'Gastonia area', '', '', '', '', 'Residential, Commercial, Drywall'],
        ['PME Painting LLC', 'Scott Long', '(704) 651-3580', '', 'pmepainting.com', 'Gastonia, NC', 'Gastonia area', '', '', '', '', 'Residential, Commercial'],
        ['R and R Painting NC LLC', '', '(704) 826-3314', '', 'r-and-r-painting-llc.com', 'Huntersville, NC', 'Huntersville, Lake Norman', '', '', '', '', 'Residential, Commercial'],
        ['Prime Painting', '', '', '', 'primepaintingclt.com', 'Huntersville, NC', 'Huntersville area', '', '', '', '', 'Residential'],
        ['4 Seasons Home Services', 'Joshua Brooks', '(240) 417-8133', '', '4seasonshomeservicesnc.com', 'Huntersville, NC', 'Huntersville area', '', '', '', '', 'Residential'],
        ['Trailblaze Paints', 'Jack MaGee', '(704) 402-0556', '', 'trailblazepaintsnc.com', 'Mooresville, NC', 'Mooresville, Lake Norman', '', '', '', '', 'Residential, Commercial'],
        ['Grace Painting & Contractors', 'Lance & Karen Hudak', '(704) 783-8900', '', 'gracepaintingcontractors.com', 'Mooresville, NC', 'Mooresville area', '', '', '', '', 'Residential, Commercial'],
        ['Lagos Painting Service', '', '', '', 'lagospaintingsvc.com', 'Mooresville, NC', 'Mooresville area', '', '', '', '', 'Residential, Commercial, Deck'],
        ['Pristine Painting', 'Carlos', '(980) 362-9677', '', 'pristinepaintingnc.com', 'Mooresville, NC', 'Mooresville area', '', '', '', '', 'Residential, Commercial'],
        ['Sherwood Painting', 'Dan Sherwood', '(704) 924-1800', '', 'sherwoodpaint.com', 'Mooresville, NC', 'Mooresville, Lake Norman', '', '', '', '', 'Residential, Commercial'],
        ['Savage Painting NC', 'Shawn Savage Jr.', '(704) 562-2127', '', 'savagepaintingnc.com', 'Mooresville, NC', 'Mooresville area', '', '', '', '', 'Residential (Veteran-owned)'],
        ["Shawn's Painting NC", 'Shawn & Deb Savage', '(704) 495-4190', '', 'shawnspaintingnc.com', 'Mooresville, NC', 'Mooresville area', '', '', '', '', 'Residential, Commercial, Drywall'],
        ['JB Painting Solutions', 'John', '(704) 728-5058', '', 'jbpaintingsolutions.com', 'Mooresville, NC', 'Mooresville, Lake Norman', '', '', '', '', 'Residential'],
        ['Blessing Pro Painters', '', '(828) 640-1280', '', 'blessingpropainters.com', 'Mooresville, NC', 'Mooresville area', '', '', '', '', 'Residential, Commercial'],
        ['Hood Paint Co. Inc.', 'James G. Hood', '(803) 327-1129', '', 'hoodpaintco.com', 'Rock Hill, SC', 'Rock Hill area', '', '', '', '', 'Residential, Commercial'],
        ['Brush Masters Painting', 'David Dennis', '(803) 324-4202', '', 'brushmasterssc.com', 'Rock Hill, SC', 'Rock Hill area', '', '', '', '', 'Residential, Commercial'],
        ["Cannon's Painting Company LLC", 'Sharon Cannon', '(803) 984-0479', '', 'cannonspainting.com', 'Rock Hill, SC', 'Rock Hill area', '', '', '', '', 'Residential, Commercial'],
        ["Murillo's Paint Stucco and Drywall", '', '(803) 448-9988', '', 'murillospaintstuccoanddrywall.com', 'Rock Hill, SC', 'Rock Hill area', '', '', '', '', 'Residential, Commercial, Stucco, Drywall'],
        ['Juan Painter', '', '(803) 230-5051', '', 'juan-painter.com', 'Rock Hill, SC', 'Rock Hill area', '', '', '', '', 'Residential, Commercial'],
        ['Jones Drywall & Painting', '', '(803) 207-9460', '', 'jonesdrywallsc.com', 'Rock Hill, SC', 'Rock Hill area', '', '', '', '', 'Residential, Commercial, Drywall'],
        ['King Paint Company', 'Jason Fitzgerald', '(803) 717-2468', '', 'kingpaintcompany.com', 'Fort Mill, SC', 'Fort Mill, Rock Hill', '', '', '', '', 'Residential, Commercial, Construction'],
        ["Callahan's Painting", '', '(803) 548-0085', '', 'callahanspainting.com', 'Fort Mill, SC', 'Fort Mill area', '', '', '', '', 'Residential, Commercial, Construction'],
        ['Small Town Paint Co.', '', '(704) 774-6149', '', 'smalltownpaintco.com', 'Fort Mill, SC', 'Fort Mill, Matthews', '', '', '', '', 'Residential, Cabinet, Deck'],
        ["Ain't Just Paint Divas", 'Michelle', '(803) 804-4027', '', 'aintjustpaintdivas.com', 'Fort Mill, SC', 'Fort Mill area', '', '', '', '', 'Residential, Commercial'],
        ['Terry Painting', '', '(866) 924-4949', '', 'terrypainting.com', 'Waxhaw, NC', 'Waxhaw, Monroe', '', '', '', '', 'Residential, Commercial'],
        ['Gray Daze Contracting', 'Gary Gray', '(770) 752-7010', '', 'graydaze.com', 'Charlotte, NC', 'Charlotte area', '', '', '', '', 'Commercial'],
        ['Paint EZ of Lake Norman', '', '(704) 313-0703', '', 'paintez.com/lake-norman', 'Mooresville, NC', 'Lake Norman, Concord', '', '', '', '', 'Residential, Commercial'],
        ['Groovy Hues of South Charlotte', 'Marta C. Montoya', '(704) 486-2211', '', 'groovyhues.com/south-charlotte-nc', 'Indian Trail, NC', 'South Charlotte, Indian Trail', '', '', '', '', 'Residential, Commercial - Franchise/local owner'],
    ]

    sheets.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range='Sheet1!A1',
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body={'values': rows}
    ).execute()

    print(f"Done! {len(rows)} painting companies added to the sheet.")
    print(f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")

if __name__ == '__main__':
    main()
