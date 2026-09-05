# Bank Policy Ingestion Sheet — Home Loan (HL) Master Questionnaire

> **Document Purpose**: This document is to be completed by the Bank's Relationship Manager (RM), Credit Policy Head, or Product Manager. **Every parameter and question listed here directly correlates with the DigitalDSA Home Loan form system (17 distinct pages, 100+ questions) and the DigitalDSA Rule Engine**.
>
> **Why 100% Completeness Matters**: The DigitalDSA platform evaluates loan applications in real-time across eligibility, FOIR, LTV, LCR, property compliance, income haircuts, and risk scoring. Any blank cell forces the engine to apply conservative default fallbacks, which may result in false rejections or lower loan offers for your institution.
>
> **Instructions**: 
> 1. Complete **all sections**.
> 2. System variable names are provided in brackets `[like_this]` for direct automated ingestion into our Policy Management System (PMS).
> 3. Where dropdowns or choices are provided, clearly tick or circle the appropriate policy option.

---

## 1. Bank & Product Scope

| Field | System Key | Description | Bank Selection / Value |
| :--- | :--- | :--- | :--- |
| **Bank / Institution Name** | `lenderName` | Official registered name of lending institution | |
| **Lender ID / Code** | `lenderId` | Short unique slug (e.g., `sbi`, `hdfc-bank`, `icici`, `tata-capital`) | |
| **Lender Classification** | `classification` | Statutory regulatory classification | [ ] `GOV` (Public Sector Bank)<br>[ ] `PVT` (Private Bank)<br>[ ] `NBFC` (Non-Banking Financial Co)<br>[ ] `HFC` (Housing Finance Co)<br>[ ] `SFB` (Small Finance Bank) |
| **Supported HL Scopes** | `loanType` | Which Home Loan scopes does your institution fund? (Select all that apply) | [ ] `New Loan`<br>[ ] `Balance Transfer Only`<br>[ ] `Balance Transfer With Top-up`<br>[ ] `Top-up Only` |
| **Product Variants Offered** | `productVariants` | Specific variants supported under Home Loan | [ ] Standard Home Loan (Flat / House / Floor)<br>[ ] Composite Loan (Plot Purchase + Construction)<br>[ ] Home Improvement / Renovation Loan<br>[ ] Home Extension Loan |
| **Policy Effective Date** | `validFrom` | Date from which this circular/policy is effective | `DD / MM / YYYY` |
| **Policy Circular Number** | `circularRef` | Internal circular/notification reference code | |
| **Completed By (RM / Credit)** | `completedBy` | Name, Designation, Official Email & Contact No. | |

---

## 2. Case Intake & Prior Rejection Policy (`caseIntake_homeLoan`)

> *Handles applicants who have recently applied elsewhere or received previous sanctions.*

| Parameter | System Key | Bank Rule / Options | Bank Value / Details |
| :--- | :--- | :--- | :--- |
| **Fresh Assessment** | `assessmentStatus: fresh` | Standard assessment without prior history | [ ] Standard processing |
| **Cooling Period for Rejected Applicants** | `assessmentStatus: rejected` | Minimum waiting period after rejection by another lender before your bank will reconsider the applicant | [ ] `No cooling period (immediate)`<br>[ ] `30 Days`<br>[ ] `90 Days (3 Months)`<br>[ ] `180 Days (6 Months)` |
| **Rejection Reason Policies** | `rejectionReasons` | Will your bank consider an applicant recently rejected elsewhere for: | |
| - *Low CIBIL / Bureau score* | `low_cibil` | Accepted if score currently meets bank floor? | [ ] Yes [ ] No |
| - *Insufficient Income / FOIR* | `insufficient_income` | Accepted if co-applicant added or tenure extended? | [ ] Yes [ ] No |
| - *Property Legal / Technical Issues* | `property_issues` | Accepted if applying for a different property? | [ ] Yes [ ] No |
| - *Incomplete Documentation* | `incomplete_docs` | Accepted once complete documents provided? | [ ] Yes [ ] No |
| - *Profile / Employer Mismatch* | `profile_mismatch` | Accepted if verified under bank's approved list? | [ ] Yes [ ] No |
| **Sanctioned but Not Disbursed Policy** | `assessmentStatus: sanctioned_not_disbursed` | Will your bank take over a freshly sanctioned file from another bank prior to first disbursement? | [ ] `Yes, treated as Fresh`<br>[ ] `Yes, treated as Balance Transfer`<br>[ ] `No` |

---

## 3. Pre-Sanction & Property Search Policy (`sanctionProfile_homeLoan`)

> *Governs applicants who have NOT yet identified a property (`propertyIdentified == 'No'`) and seek pre-approval.*

| Parameter | System Key | Bank Rule / Options | Bank Value / Details |
| :--- | :--- | :--- | :--- |
| **Pre-Approval Facility Offered?** | `preApprovalOffered` | Does your bank issue pre-sanction letters before property finalization? | [ ] Yes [ ] No |
| **Validity of Pre-Approval** | `preApprovalValidity` | Maximum validity period of pre-sanction letter | [ ] `60 Days` [ ] `90 Days` [ ] `180 Days` |
| **Sanction Basis Supported** | `sanctionType` | Methods allowed for computing pre-sanction limit: | [ ] `Based On Eligibility` (Income/FOIR)<br>[ ] `Based on Downpayment` (Budget-based)<br>[ ] Both |
| **Bridge Gap with Personal Loan?** | `withPersonalLoan` | If downpayment + pre-approved loan falls short, does your bank allow co-sanctioning an unsecured Personal Loan for equity/stamp duty? | [ ] `Allowed (Combo HL + PL)`<br>[ ] `Strictly Prohibited` |
| **Pre-Sanction Max Tenure** | `mortgageYear` | Max loan term granted on pre-approval (without property details) | ____ Years (Standard: 20–30 Years) |

---

## 4. Property Location & Statutory Area Classification (`propertyLocation_homeLoan`)

> *The system classifies property statutory location into 5 distinct statutory area types (`propertyAreaType`). Each has profound legal and technical implications.*

| Statutory Area Type | System Key | Bank Acceptance Policy | Special Covenants / Conditions |
| :--- | :--- | :--- | :--- |
| **Planned Authority Area** | `PLANNED_AUTHORITY` | Statutory development authority layouts (e.g., DDA, BDA, NOIDA, MHADA, HUDA, CIDCO, MMRDA) | [ ] `Accepted by all branches`<br>[ ] `Accepted only in approved sectors` |
| **Converted Residential Land** | `CONVERTED_RESIDENTIAL` | Agricultural land officially converted to Non-Agricultural (NA) residential land by District Collector/SDM | [ ] `Accepted if NA order registered`<br>[ ] `Accepted if NA pending`<br>[ ] `Not accepted` |
| **Old Municipal / City Abadi** | `OLD_MUNICIPAL` | Walled city, Lal Dora, Gaothan, or historic municipal corporation limits | [ ] `Accepted with registered sale deed`<br>[ ] `Accepted only with sanction plan`<br>[ ] `Not accepted` |
| **Local Colony / Regularized** | `LOCAL_COLONY` | Private colonies regularized or unregularized by state government | [ ] `Only Regularized Colonies accepted`<br>[ ] `Unregularized accepted (HFC/NBFC only)`<br>[ ] `Not accepted` |
| **Geographic Negative Area List** | `geo.excludedCities` `negativePincodes` | List any specific Pincodes, Municipalities, or Districts completely blacklisted by your credit policy | Attach list or specify: |
| **Minimum Property Carpet Area** | `minCarpetArea` | Minimum usable carpet area in square feet | ____ sq.ft (e.g., `250 sq.ft` for metro, `400 sq.ft` elsewhere) |

---

## 5. Property Technical & Structural Character (`propertyCharacter_homeLoan`)

| Property Form Factor | System Key | Accepted? | Max LTV Cap (%) | Max Allowable Age (Years) | Special Rules |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Flat / Apartment** | `Flat` | [ ] Yes [ ] No | ____% | ____ Years | |
| **Independent House / Villa** | `House` | [ ] Yes [ ] No | ____% | ____ Years | Land ownership must be freehold / valid lease |
| **Builder Floor** | `Floor` | [ ] Yes [ ] No | ____% | ____ Years | Separate electricity/water meters + roof rights policy |

### 5A. Construction Stage & Builder Criteria

| Parameter | System Key | Bank Policy | Required Supporting Documents |
| :--- | :--- | :--- | :--- |
| **Ready To Move (RTM)** | `PropertyStage: Ready To Move` | Occupancy Certificate (OC) / Completion Certificate (CC) mandatory? | [ ] `OC mandatory for all flats`<br>[ ] `CC acceptable`<br>[ ] `B-Khata / Assessment OK` |
| **Under Construction (UC)** | `PropertyStage: Under Construction` | RERA Registration mandatory? | [ ] `Mandatory (No exceptions)`<br>[ ] `Exempt if project < 8 units / 500 sqm`<br>[ ] `Not mandatory` |
| **Approved Builder List / APF** | `builderRole` `caseAvailableLenders` | Does your bank require the project to be Pre-Approved (APF)? | [ ] `APF mandatory for UC flats`<br>[ ] `Non-APF allowed with separate legal/tech report`<br>[ ] `All RERA projects allowed` |
| **Joint Development Agreement (JDA)** | `builderRole: joint_development` | Policy on builder floors / flats constructed under JDA with land owner: | [ ] `Accepted if registered JDA + POA on record`<br>[ ] `Accepted only on builder's allocated share`<br>[ ] `Not accepted` |

---

## 6. Compliance, Approvals & Title Chain (`complianceLegal_homeLoan`)

### 6A. Plan Sanction & Approvals

| Parameter | System Key | Policy / Tolerance | Notes / Penalty |
| :--- | :--- | :--- | :--- |
| **Sanctioned Building Plan** | `municipalApproval` | [ ] `Sanctioned plan strictly mandatory`<br>[ ] `Deviations up to 10% allowed`<br>[ ] `Deviations up to 25% allowed with penalty / structural stability cert`<br>[ ] `Plan not required if > 20 yrs old` | |
| **Unauthorized Additions** | `unauthorizedAdditions` | Extra floor, balcony enclosure, or room without municipal approval: | [ ] `NONE allowed (strict zero tolerance)`<br>[ ] `MINOR allowed (not counted in valuation)`<br>[ ] `MAJOR allowed with compounding proof` |
| **Property Tax Status** | `municipalTaxStatus` | Latest municipal property tax receipt status: | [ ] `Latest paid receipt mandatory`<br>[ ] `Can be cleared prior to disbursement` |
| **Gram Panchayat Approvals** | `gramPanchayatPermission` | Construction within Gram Panchayat / Village limits: | [ ] `Accepted if layout approved by DTCP/DA`<br>[ ] `Accepted with Panchayat NOC only`<br>[ ] `Strictly Not Accepted` |

### 6B. Title Chain & Documentation Readiness

| Title Parameter | System Key | Bank Requirement | Risk Mitigant Required |
| :--- | :--- | :--- | :--- |
| **Minimum Title Chain Period** | `titleChainStatus` | Number of years of unbroken prior title search required | [ ] `13 Years`<br>[ ] `30 Years (Standard PSU / Legal)`<br>[ ] `Since original allotment / mother deed` |
| **Missing Prior Deeds** | `titleChainStatus: CURRENT_OK_PREV_MISSING` | If current sale deed is intact but an intermediate prior deed is missing: | [ ] `Accepted with Certified Copy + FIR + Public Notice + Indemnity`<br>[ ] `Strictly Rejected` |
| **Original Documents Lost by Owner** | `titleDocsMissingReason: LOST_BY_OWNER` | If the current owner has lost original sale deeds: | [ ] `Rejected by bank policy`<br>[ ] `Accepted with Court certified copy, 2 newspapers public notice, and equitable mortgage deposit` |
| **Encumbrance Certificate (EC)** | `encumbranceCertStatus` | Nil-Encumbrance Certificate requirement: | Minimum period required: ____ Years (Standard: 13–30 yrs) |
| **Revenue Records & Mutation** | `revenueRecordMutation` | 7/12 Extract / Jamabandi / Patta / Khata mutation: | [ ] `Mutation in seller's name mandatory before sanction`<br>[ ] `Mutation can be completed before disbursement`<br>[ ] `Not mandatory for high-rise flats` |

---

## 7. Counterparty & Resale Seller Verification (`sellerTransaction_homeLoan`)

> *Applicable for resale transactions (`purchaseType: resale_normal` or `resale_endorsement`).*

| Seller Attribute | System Key | Bank Policy | Conditions / Safeguards |
| :--- | :--- | :--- | :--- |
| **Seller Ownership Form** | `sellerOwnershipType` | [ ] `Sole Owner` [ ] `Joint Owners`<br>[ ] `Inherited Property`<br>[ ] `Power of Attorney (POA) Holder` | If Inherited: [ ] Legal heirship / Succession cert mandatory<br>If POA: [ ] Registered POA with alive certificate mandatory |
| **Suraj Lamp Compliance (Agreement to Sell + POA)** | `propertyAcquisitionMethod: AGREEMENT_POA` | Property acquired by seller via Agreement to Sell + General Power of Attorney (GPA / Will) without registered sale deed: | [ ] `Strictly Prohibited (Supreme Court ruling)`<br>[ ] `Accepted if registered tripartite agreement done`<br>[ ] `Financed only through select NBFCs (Specify:)` |
| **Seller Has Existing Loan** | `sellerOnLoan` | Seller's original title deeds deposited with an existing lender (Bank / NBFC / HFC): | [ ] `Accepted: Bank issues direct payoff cheque to seller's lender against list of documents (LOD)`<br>[ ] `Seller must close loan independently first` |
| **Max Payoff Processing Time** | `sellerLoanPayoff` | Maximum turnaround days allowed to retrieve original deeds from seller's lender after payoff | ____ Business Days |
| **Recent Registry Seasoning** | `lastRegistryDuration` | If seller acquired the property very recently: | [ ] `No minimum seasoning required`<br>[ ] `Minimum 6 Months vintage required`<br>[ ] `Minimum 12 Months vintage required` (Anti-flipping check) |
| **Outstanding Builder Demand on Resale** | `isAnyBuilderDemand` | Any pending transfer charges, maintenance, or escalation due to builder: | [ ] `Builder NOC / Clearance Certificate mandatory prior to disbursement`<br>[ ] `Can be deducted from loan disbursement` |

---

## 8. Direct Authority Purchases (`sellerTransaction_authority_homeLoan`)

> *Applicable when buying directly from government development bodies (e.g. DDA, MHADA, HUDA, BDA).*

| Parameter | System Key | Bank Policy |
| :--- | :--- | :--- |
| **Allotment Letter Status** | `allotmentLetterStatus` | [ ] `Original Allotment Letter mandatory`<br>[ ] `Certified copy acceptable`<br>[ ] `Provisional allotment acceptable` |
| **Tripartite Agreement (TPA)** | `tpaRequired` | Does your bank require a formal Tripartite Agreement signed by the Authority, Borrower, and Bank? | [ ] `Mandatory prior to disbursement`<br>[ ] `Authority Permission to Mortgage (PTM) sufficient` |
| **Pending Dues to Authority** | `authorityPaymentStatus` | If installments are still pending to the authority: | [ ] `Bank disburses directly to Authority as per payment schedule`<br>[ ] `Allotment must be 100% paid up by borrower first` |
| **Conveyance Deed Timeline** | `possessionCertificateStatus` | Maximum time allowed after possession to execute and deposit the registered Conveyance Deed / Lease Deed with the bank: | ____ Months (Standard: 6–12 Months) |

---

## 9. Deal Financials, Three-Cost Valuation, LTV & LCR (`dealFinancials_homeLoan`)

### 9A. The 3-Cost Valuation Model & LTV Caps

DigitalDSA computes loan eligibility against three distinct property values:
1. **Market Value (`marketValue`)**: Assessed fair market value by bank's empaneled valuer.
2. **Agreed Deal Cost (`propCost`)**: Actual purchase price agreed between buyer and seller.
3. **Registry / Circle Rate Value (`registryValue`)**: Value declared for stamp duty registration.

| Property Valuation Tier | Statutory RBI Cap | Bank Standard LTV Cap (%) | Valuation Basis Applied |
| :--- | :---: | :---: | :--- |
| **Up to ₹30 Lakhs** | **90%** | ____% | [ ] `Lower of Market Value & Agreement Value`<br>[ ] `Agreement Value (propCost)`<br>[ ] `Market Value (bank valuation)` |
| **₹30 Lakhs to ₹75 Lakhs** | **80%** | ____% | [ ] `Lower of Market Value & Agreement Value`<br>[ ] `Agreement Value (propCost)`<br>[ ] `Market Value (bank valuation)` |
| **Above ₹75 Lakhs** | **75%** | ____% | [ ] `Lower of Market Value & Agreement Value`<br>[ ] `Agreement Value (propCost)`<br>[ ] `Market Value (bank valuation)` |
| **Inclusive of Stamp Duty & Reg?** | `includeStampDuty` | Are stamp duty, registration charges, and transfer fees capitalised into project cost for LTV? | [ ] `Yes (Strictly properties ≤ ₹30 Lakhs as per RBI)`<br>[ ] `No, borrower must fund 100% out of pocket` |

### 9B. Loan-to-Cost / Loan-to-Registry Ratio (LCR) — Seller Disbursement Release

> *Critical parameter governing the cheque amount handed to the seller on registration day.*

| Parameter | System Key | Bank Value / Rule | Description |
| :--- | :--- | :---: | :--- |
| **Max LCR Cap** | `max_lcr` | **____%** | Maximum loan disbursement released against the registered deed value (e.g. `90%` of `registryValue`) |
| **Advance Token Adjustment** | `advanceInAgreement` | [ ] `Deducted from registration release`<br>[ ] `Not deducted (counted in overall equity)` | How token money / advance paid by buyer is treated on registration day |
| **NBFC Dual-Tranche HL/LAP Split** | `trancheSplit` | [ ] Yes [ ] No<br>Tranche 1 (HL ROI): ____%<br>Tranche 2 (LAP ROI): ____% | If agreement value > registry value, does your institution fund the differential under a secondary LAP tranche? |

### 9C. Downpayment & Own Contribution

| Parameter | System Key | Requirement |
| :--- | :--- | :--- |
| **Minimum Borrower Equity (Own Contribution)** | `deposit` | Minimum % of total deal value borrower must contribute from own legitimate banking channels (e.g. `10%` to `20%`) |
| **Proof of Own Contribution Required** | `marginMoneyProof` | [ ] `100% margin money payment receipts verified before first disbursement`<br>[ ] `Pro-rata verification along with slab disbursements` |

### 9D. Bank Auction Purchases & Registration Timeline

| Acquisition & Execution Metric | System Key | Bank Requirement / Policy | Specific Conditions |
| :--- | :--- | :--- | :--- |
| **Bank SARFAESI / DRT Auction Property** | `auctionPropertyStatus` | [ ] `STANDARD` (Open market purchase)<br>[ ] `AUCTION_AWARE` (Purchased via bank SARFAESI / DRT e-auction)<br>[ ] `AUCTION_UNAWARE` | [ ] `Funded at standard HL terms`<br>[ ] `Max LTV capped at ____% of auction bid price`<br>[ ] `Requires 25% deposit proof + DRT / Court clearance certificate`<br>[ ] `Strictly Not Funded` |
| **Disbursement to Registration Turnaround** | `registrationTimeline` | Permissible time window between cheque release and registered sale deed deposit: | [ ] `Same Day (Cheque handed over in Sub-Registrar Office)`<br>[ ] `Within 30 Days`<br>[ ] `30 to 60 Days (with tripartite / escrow arrangement)` |

---

## 10. Balance Transfer (BT) & Top-Up Criteria (`btExistingLoan_homeLoan` & `loanRequirements_homeLoan`)

### 10A. Balance Transfer Eligibility

| Parameter | System Key | Policy Requirement | Notes / Exceptions |
| :--- | :--- | :--- | :--- |
| **Minimum Loan Vintage** | `btEmisPaid` | Minimum consecutive EMIs successfully paid to existing lender: | [ ] `6 Months / EMIs`<br>[ ] `12 Months / EMIs (Standard)`<br>[ ] `18 Months / EMIs` |
| **12-Month EMI Bounce Tolerance** | `emiBounceHistory` | Permissible banking EMI bounces in the preceding 12 months: | [ ] `Zero tolerance (0 bounces only)`<br>[ ] `Max 1 bounce (if cleared within same month)`<br>[ ] `Max 2 bounces (with strong credit justification)` |
| **Original Disbursement Vintage** | `loanDisbursementDate` | Minimum months elapsed since original loan disbursement: | ____ Months |
| **Acceptable Existing Lenders** | `selectSingleBank` | Categories of lenders from which BT is accepted: | [ ] `All Scheduled Commercial Banks (PSB / PVT)`<br>[ ] `All NHB-Registered HFCs`<br>[ ] `Select NBFCs (Specify:)`<br>[ ] `Co-operative Banks (with special approval)` |
| **Foreclosure Charges Charged by Source** | `foreclosureCharges` | RBI compliance: | 0% for floating rate individual loans (RBI mandate) |

### 10B. Top-Up Facilities

| Parameter | System Key | Bank Limit / Policy | Notes |
| :--- | :--- | :--- | :--- |
| **Maximum Top-Up Loan Amount** | `topUpAmount` | Up to ₹ ________ or ____% of original sanction | Minimum ticket size: ₹ ________ |
| **Combined Exposure LTV Cap** | `topUpLtvCap` | Maximum combined LTV (Home Loan Outstanding + Top-up Loan) against current property market value: | [ ] `70%`<br>[ ] `75%`<br>[ ] `80%`<br>[ ] Same as standard HL LTV |
| **Maximum Top-Up Tenure** | `topUpTenure` | Maximum repayment period for the Top-up portion: | ____ Years (Cannot exceed remaining HL tenure) |
| **Permissible Top-Up Purposes** | `topUpPurpose` | Select all accepted end-uses: | [ ] `RENOVATION` [ ] `EXTENSION` [ ] `FURNISHING`<br>[ ] `MEDICAL` [ ] `EDUCATION` [ ] `BUSINESS`<br>[ ] `DEBT_CONSOLIDATION` [ ] `PERSONAL` |
| **Backend System Accounting** | `btTopUpTreatment` | How does your core banking system (CBS) book a BT + Top-up deal? | [ ] `Single Combined Loan` (single loan account, blended tenure, one EMI)<br>[ ] `Two Separate Loans` (HL account + distinct Top-up account with independent tenures/EMIs) |

---

## 11. Applicant Eligibility, Co-Applicants & Guarantors (`tellUs_homeLoan` & `applicantProfilePage`)

### 11A. Individual Applicants — Age & Vintage Criteria

| Parameter | System Key | Salaried Individuals | Self-Employed Individuals (SEP / SENP) |
| :--- | :--- | :---: | :---: |
| **Minimum Age at Entry** | `minAge` | ____ Years (Min: 18/21) | ____ Years (Min: 21/25) |
| **Maximum Age at Entry** | `maxAge` | ____ Years (Max: 58/60) | ____ Years (Max: 65) |
| **Maximum Age at Loan Maturity** | `maxAgeAtMaturity` | ____ Years (Standard: 60/65) | ____ Years (Standard: 65/70/75) |
| **Minimum Total Work / Business Vintage** | `totalExperience` | ____ Years total experience | ____ Years in same business line |
| **Minimum Vintage with Current Employer** | `currentJobVintage` | ____ Months (e.g. 6–12 months) | N/A |
| **Minimum Business Continuity Proof** | `businessVintageProof` | N/A | [ ] 2 Years ITR [ ] 3 Years ITR [ ] GST cert |

### 11B. Demographics, Education & Priority Sector Lending (PSL) (`applicantProfilePage`)

> *Captured on the Applicant Profile page. Directly determines Priority Sector Lending (PSL) eligibility, government subsidy qualifications (e.g., PMAY), and underwriting risk weights.*

| Demographic Attribute | System Key | Form Options | Bank Policy & Underwriting Impact |
| :--- | :--- | :--- | :--- |
| **Educational Qualification** | `education` | [ ] `below_10th`<br>[ ] `10th_pass`<br>[ ] `12th_pass`<br>[ ] `graduate_plus`<br>[ ] `post_graduate`<br>[ ] `professional` *(CA, Doctor, Lawyer)* | [ ] Minimum qualification required (Specify: ________)<br>[ ] No minimum educational restriction<br>[ ] Higher FOIR / preferential pricing for professionals |
| **Social / Caste Category** | `casteCategory` | [ ] `General`<br>[ ] `OBC` *(Other Backward Class)*<br>[ ] `SC` *(Scheduled Caste)*<br>[ ] `ST` *(Scheduled Tribe)* | [ ] Tracked for Priority Sector Lending (PSL) quotas<br>[ ] Concessional processing fees for SC/ST/OBC<br>[ ] Neutral underwriting |
| **Religious Classification** | `religion` | [ ] `hindu` [ ] `muslim`<br>[ ] `christian` [ ] `sikh`<br>[ ] `buddhist_jain` [ ] `others` | [ ] Statutory RBI PSL Minority Communities reporting<br>[ ] Neutral underwriting |
| **Existing Residential Properties Owned** | `ownedProperties` | [ ] `0` *(First-time homebuyer)*<br>[ ] `1` *(Second home)*<br>[ ] `2`<br>[ ] `3+` *(Multi-property investor)* | [ ] First-time buyers eligible for PMAY CLSS interest subsidy<br>[ ] 3rd+ residential property treated as commercial / investor exposure (reduced LTV cap: ____%) |
| **Differently-Abled / PWD Status** | `disability` | [ ] `No`<br>[ ] `Yes` | [ ] Special interest concession offered (____ bps)<br>[ ] Dedicated processing / doorstep facility<br>[ ] Standard terms |
| **Marital Status** | `maritalStatus` | [ ] `single`<br>[ ] `married`<br>[ ] `divorced`<br>[ ] `widowed`<br>[ ] `separated` | [ ] Single / Unmarried women accepted independently<br>[ ] Divorced applicants accepted with registered decree + alimony deed<br>[ ] Separated applicants accepted with legal declaration |

### 11C. Residence Location, Office Proximity & Outstation Borrowers (`applicantResidence`)

> *Governs branch distance, outstation buyers, and geographic lending limitations.*

| Geographical Metric | System Key | Bank Requirement | Permissible Options / Conditions |
| :--- | :--- | :--- | :--- |
| **Residence Relative to Property** | `applicantResidenceType` | [ ] `SAME_CITY`<br>[ ] `DIFFERENT_CITY`<br>[ ] `DIFFERENT_STATE` | [ ] `SAME_CITY`: Standard underwriting<br>[ ] `DIFFERENT_CITY`: Allowed within bank's branch footprint<br>[ ] `DIFFERENT_STATE`: Outstation borrower policy applies |
| **Outstation Borrower Policy** | `outstationBorrowerPolicy` | When applicant lives in a different state from property: | [ ] `Accepted if primary bank branch exists in both cities`<br>[ ] `Accepted ONLY with a local resident co-applicant / guarantor`<br>[ ] `Strictly Restricted / Not Accepted` |
| **Maximum Branch Proximity Radius** | `maxBranchDistanceKm` | Max allowable distance between property / residence and nearest bank branch: | [ ] Within **____ km** (Standard: `35 km` metro, `50 km` non-metro)<br>[ ] Anywhere within state limits |
| **Company Corporate Office Location** | `companyOfficeLocation` | For corporate borrowers / sole proprietors: | Must be within bank's operational branch jurisdiction |

### 11D. Non-Resident Indians (NRI), OCI & GPA Holder Governance (`GPAOfNriApplicant`)

> *Activated when all standalone individuals are NRI (`allStandaloneIndividualsNri == true`).*

| Parameter | System Key | Policy Requirement | Conditions / Standards |
| :--- | :--- | :--- | :--- |
| **NRI Applicants Funded?** | `isNRI` `ApplicantIsNRI` | [ ] `Yes`<br>[ ] `No`<br>[ ] `Only with Resident Indian Co-Applicant` | Minimum overseas stay: ____ Years<br>Valid Work Permit / Visa mandatory |
| **General Power of Attorney (GPA)** | `gpaDetails` | Mandatory when all individual borrowers are NRI: | [ ] `Mandatory for all NRI files`<br>[ ] `Exempt if NRI physically present in India for execution` |
| **Eligible GPA Holders** | `gpaEligibility` | Who is legally permitted to hold GPA on the loan? | [ ] `Strictly Close Blood Relatives` *(Spouse, Parent, Sibling, Child)*<br>[ ] `Extended Family accepted`<br>[ ] `Any legal resident Indian representative` |
| **Consular Attestation & Adjudication** | `gpaAdjudicationTimeline` | Procedure for overseas GPA execution: | Must be signed at Indian Embassy / Consulate abroad and adjudicated in India within **____ days** (Standard: `90 Days`) |
| **Minimum Overseas Earnings Floor** | `nriMinSalary` | Minimum net monthly income required: | [ ] GCC / Middle East: `AED / SAR ________`<br>[ ] US / UK / Europe: `USD / GBP / EUR ________`<br>[ ] Singapore / Australia: `SGD / AUD ________` |
| **Mandatory Bank Account in India** | `nriAccountType` | Mode of loan EMI servicing: | [ ] `NRE Account` [ ] `NRO Account`<br>[ ] Direct inward foreign wire remittance |
| **Country Exclusions (FATF)** | `nriCountry` | List any prohibited countries: | [ ] All FATF grey / blacklisted countries strictly barred |

### 11E. Corporate Borrowers, LLPs & Inline Director Management (`DirectorFormModal`)

| Corporate Parameter | System Key | Policy Requirement | Conditions |
| :--- | :--- | :--- | :--- |
| **Accepted Company Entities** | `companyType` | [ ] `Pvt Ltd Company`<br>[ ] `Public Ltd Company`<br>[ ] `Limited Liability Partnership (LLP)`<br>[ ] `Partnership Firm`<br>[ ] `One Person Company (OPC)`<br>[ ] `Trust / Society` | [ ] Accepted as primary borrower<br>[ ] Accepted as co-borrower / collateral guarantor only |
| **Minimum Operating Vintage** | `companyVintage` | Minimum years of incorporated operations: | ____ Years (Standard: 2–3 Years with audited balance sheets) |
| **Director Personal Guarantee Mandate** | `directorGuarantee` | Threshold requiring personal guarantee: | [ ] `All directors holding > 10% equity`<br>[ ] `All directors holding > 26% equity`<br>[ ] `All executive / promoter directors regardless of share`<br>[ ] `100% of all directors` |
| **Family-Controlled Corporate Borrower** | `familyControlled` | When immediate family members hold ≥ 51% equity: | [ ] `Family income pooling allowed (Corporate + Personal Cash Flows)`<br>[ ] `Evaluated strictly as independent corporate balance sheet` |
| **Non-Borrower Directors (CIBIL Only)** | `cibil_only` | Directors not tagged as co-applicants: | [ ] `CIBIL scrub mandatory for all promoter directors`<br>[ ] `Exempt if non-executive / independent director` |

### 11F. Co-Applicant Relationship & Income Pooling Master Matrix (`RelationShip.svelte`)

> *The DigitalDSA Relationship Engine maps 16+ pairwise relationships. Specify whether each combination is accepted for (1) joint property co-ownership, and (2) income pooling for loan eligibility.*

| Co-Applicant Pairwise Relationship | Permissible Relationship Category | Accepted if Co-Owner? (`onProperty: true`) | Accepted if Non-Owner? (`onProperty: false`) | Income Pooled in FOIR? | Special Bank Covenants |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Husband & Wife** | Direct Family | [ ] Yes [ ] No | [ ] Yes [ ] No | [ ] Yes [ ] No | Standard co-borrower pair |
| **Father & Son** | Direct Family | [ ] Yes [ ] No | [ ] Yes [ ] No | [ ] Yes [ ] No | If multiple sons, all sons must sign NOC or be co-applicants |
| **Father & Unmarried Daughter** | Direct Family | [ ] Yes [ ] No | [ ] Yes [ ] No | [ ] Yes [ ] No | Income clubbed until marriage |
| **Father & Married Daughter** | Direct Family | [ ] Yes [ ] No | [ ] Yes [ ] No | [ ] Yes [ ] No | [ ] Allowed only if sole child/heir<br>[ ] Husband must join as co-applicant |
| **Mother & Son** | Direct Family | [ ] Yes [ ] No | [ ] Yes [ ] No | [ ] Yes [ ] No | Mother can be non-financial co-owner |
| **Mother & Unmarried Daughter** | Direct Family | [ ] Yes [ ] No | [ ] Yes [ ] No | [ ] Yes [ ] No | |
| **Mother & Married Daughter** | Direct Family | [ ] Yes [ ] No | [ ] Yes [ ] No | [ ] Yes [ ] No | Restricted |
| **Brother & Brother** | Direct Family | [ ] Yes [ ] No | [ ] Yes [ ] No | [ ] Yes [ ] No | [ ] Allowed ONLY if joint co-owners residing together<br>[ ] Independent legal search on partition |
| **Brother & Sister (Unmarried)** | Direct Family | [ ] Yes [ ] No | [ ] Yes [ ] No | [ ] Yes [ ] No | Allowed if joint co-owners |
| **Sister & Sister (Unmarried)** | Direct Family | [ ] Yes [ ] No | [ ] Yes [ ] No | [ ] Yes [ ] No | Allowed if joint co-owners |
| **In-Laws (Father/Mother/Son/Daughter-in-law)** | In-Law Family | [ ] Yes [ ] No | [ ] Strictly No | [ ] Strictly No | Generally barred from income pooling |
| **Grandparents & Grandchildren** | Grandparent Family | [ ] Yes [ ] No | [ ] Yes [ ] No | [ ] Yes [ ] No | Allowed if legal guardian / succession deed intact |
| **Uncle / Aunt & Nephew / Niece** | Extended Family | [ ] Yes [ ] No | [ ] Strictly No | [ ] Strictly No | Barred unless verified legal heir |
| **Business Partners (as Individuals)** | Non-Family | [ ] Yes [ ] No | [ ] Strictly No | [ ] Strictly No | Commercial / LAP only, or with partnership deed |
| **Friends / Unrelated Co-Owners** | Non-Family | [ ] Yes [ ] No | [ ] Strictly No | [ ] Strictly No | [ ] Strictly Rejected (PSU / PVT)<br>[ ] Accepted by NBFCs with joint liability |
| **Non-Financial Co-Applicant** | Any Category | [ ] Yes [ ] No | [ ] Yes [ ] No | **Strictly No** | CIBIL scrubbed; no income added; onEMI can be false |
| **Personal Guarantor** | Any Category | [ ] N/A | [ ] Yes [ ] No | **Strictly No** | Signs personal guarantee; contingent liability |

### 11G. Employer Categorization & Salary Payment Mode (`salariedQuestion`)

| Salaried Profile Parameter | System Key | Bank Requirement / Policy | Notes / Cutoffs |
| :--- | :--- | :--- | :--- |
| **Super A / Navratna / Top MNC (`CAT_A`)** | `employerCategory: CAT_A` | Minimum net monthly salary: ₹ ________ | Preferential ROI: ____ bps concession |
| **Large Listed / Tier-2 (`CAT_B`)** | `employerCategory: CAT_B` | Minimum net monthly salary: ₹ ________ | Standard terms |
| **Mid-Size Pvt Ltd (`CAT_C`)** | `employerCategory: CAT_C` | Minimum net monthly salary: ₹ ________ | Minimum 2-year company vintage |
| **Government / PSU / Defence (`GOVT`)** | `employerCategory: GOVT` | Minimum net monthly salary: ₹ ________ | Extended retirement age (up to 60–65 yrs) |
| **Unlisted / Small Enterprises (`UNLISTED`)** | `employerCategory: UNLISTED` | Minimum net monthly salary: ₹ ________ | Minimum 3-year audited ITR of employer |
| **Bank Account Transfer Salary** | `salaryMode: bank_transfer` | [ ] Standard processing [ ] 3 Months payslips + 6M bank credit statement |
| **Cheque Payment Salary** | `salaryMode: cheque` | [ ] Accepted with 6M bank deposit proof [ ] Accepted with 12M ITR [ ] Not accepted |
| **Cash Salary Policy** | `salaried_cash` `salaryMode: cash` | [ ] `Strictly Auto-Rejected (Zero tolerance)`<br>[ ] `Accepted under Affordable Housing Scheme (Capped at ₹________, Max 70% LTV)` |

### 11H. Self-Employed Assessment Schemes & Surrogates (`businessQuestion`)

| Self-Employed Assessment Scheme | System Key | Acceptance Policy | Methodology / Maximum Loan Multiplier |
| :--- | :--- | :--- | :--- |
| **Traditional ITR Net Profit Method** | `assessmentMethod: ITR` | [ ] Standard Policy | Average 2–3 Years `(Net Profit + Allowable Depreciation) / 12` |
| **Banking Turnover / Cash Flow Surrogate** | `assessmentMethod: Banking` | [ ] Yes [ ] No | Evaluates **____%** of total 12-month banking credits as deemed net profit *(Standard: 8%–15%)* |
| **GST / Gross Receipts Multiplier Scheme** | `assessmentMethod: GST` | [ ] Yes [ ] No | Assesses net profit as **____%** of annual filed GST turnover |
| **Low LTV / No-Income-Proof Scheme** | `assessmentMethod: Low_LTV` | [ ] Yes [ ] No | Funds up to **____% LTV** based solely on property valuation and clean CIBIL (no ITR required) |

---

## 12. Credit Bureau Score, DPD & Default Resolution (`creditScorePage`)

### 12A. Bureau Score Thresholds

| Parameter | System Key | Standard Policy | Deviation Available |
| :--- | :--- | :---: | :--- |
| **Minimum Bureau Score Floor** | `minCreditScore` | **____ CIBIL** (e.g. 700 / 750) | Down to ____ with ____% ROI loading |
| **CIBIL Scope Applied** | `cibilScope` | Whose bureau score is evaluated? | [ ] `All Co-Applicants (Financial & Non-Financial)`<br>[ ] `Financial Co-Applicants Only`<br>[ ] `Primary Applicant Only` |
| **New to Credit (NTC / -1 / 0 Score)** | `ntcScoreAllowed` | Applicants with no prior credit history: | [ ] `Accepted at standard terms`<br>[ ] `Accepted with 5% lower LTV`<br>[ ] `Accepted only if salaried with listed company`<br>[ ] `Not accepted` |
| **Recent Credit Enquiries (Last 90 Days)** | `recentEnquiryCount` | Max bureau enquiries allowed: | [ ] `0–2` [ ] `3–5` [ ] `6+ allowed with explanation` |

### 12B. DPD & Default Resolution Policy

| Historical Credit Signal | System Key | Permissible Bank Threshold | Mandated Action / Remedy |
| :--- | :--- | :--- | :--- |
| **Lifetime EMI Bounce Count** | `emiBounceCount` | [ ] `0 Bounces (Clean history)`<br>[ ] `1 Bounce allowed`<br>[ ] `2 Bounces allowed`<br>[ ] `3+ Bounces allowed with track record` | |
| **EMI Bounce Clearance Delay** | `emiBounceClearance` | Acceptable resolution timeline for past bounces: | [ ] `same_month` (Cleared within same cycle)<br>[ ] `next_month` (Within 30 days)<br>[ ] `2_to_3_months` (60–90 DPD)<br>[ ] `over_3_months` (90+ DPD — strictly rejected)<br>[ ] `still_pending` (Active default — rejected) |
| **Settlement / Write-Off Status** | `defaultSettlementStatus` | Policy for past settled or written-off accounts: | [ ] `CLEAN` — Accounts never settled/written off<br>[ ] `SETTLED` — Allowed if settled > ____ months ago with No Due Certificate (NDC)<br>[ ] `WRITTEN_OFF` — Allowed if repaid 100% principal<br>[ ] `ACTIVE_DEFAULT` — Strictly Auto-Reject |
| **Is Defaulter Allowed?** | `isDefaulterAllowed` | Can a borrower with an active unresolved default be approved? | [ ] `Strictly No (Hard Gate)`<br>[ ] `Yes (Subprime NBFC only, with conditions:)` |

---

## 13. Income Assessment & Haircuts for All 12 Profiles (`incomeProfilesPage` & `incomeDetailsPage`)

> *Every income source is assessed independently. Specify the haircut % (deduction for variance/tax) and the exact computation methodology.*

| # | Canonical Profile ID | Profile Display Name | Accepted? | Haircut (%) | Max Contribution to Total Income (%) | Computation Methodology | Mandatory Evidence Documents |
| :-: | :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| 1 | `salaried_regular` | **Salaried — Regular** *(MNC / Listed / Large Pvt Ltd)* | [ ] Yes<br>[ ] No | ____% *(0–5%)* | 100% | Net Monthly Take-Home Salary (after PF/Tax) | 3M Salary Slips, 6M Bank Statement, Latest Form 16 |
| 2 | `salaried_government` | **Salaried — Government / PSU** *(State / Central / Defence)* | [ ] Yes<br>[ ] No | ____% *(0%)* | 100% | Net Monthly Salary (pensionable benefits noted) | 3M Pay Slips, 6M Salary Credit A/c Statement, Service ID |
| 3 | `salaried_contractual` | **Salaried — Contractual / Small Pvt Ltd** | [ ] Yes<br>[ ] No | ____% *(10–20%)* | ____% | Net Salary (averaging 6–12 months) | Appointment Contract, 12M Bank Statement, 2Y ITR / Form 16 |
| 4 | `business_proprietorship` | **Self-Employed Non-Professional (SENP)** *(Proprietorship)* | [ ] Yes<br>[ ] No | ____% *(20–35%)* | ____% | `Average Net Profit after Tax / 12` + allowable depreciation addback | 2–3Y Audited ITR with Computation, Balance Sheet, 12M Current A/c Stmt, GST Returns |
| 5 | `business_partnership` | **Partnership Firm — Partner's Share** | [ ] Yes<br>[ ] No | ____% *(25–35%)* | ____% | `(Partner's Salary + Share of Profit) / 12` | Partnership Deed, 2Y Firm & Partner ITR, Capital A/c Stmt |
| 6 | `director_company` | **Director — Pvt Ltd / Public Ltd** | [ ] Yes<br>[ ] No | ____% *(20–30%)* | ____% | `(Director Remuneration + Dividends) / 12` | Form 16 / 2Y ITR, Board Resolution, Shareholding Pattern, 12M Bank Statement |
| 7 | `professional_practice` | **Self-Employed Professional (SEP)** *(Doctors, CAs, Architects, Lawyers)* | [ ] Yes<br>[ ] No | ____% *(15–25%)* | 100% | Gross Professional Receipts × ____% or Net Profit after Tax / 12 | Professional Degree Cert, 2Y ITR, 12M Bank Statement |
| 8 | `rental_income` | **Rental Income** *(Commercial / Residential)* | [ ] Yes<br>[ ] No | ____% *(20–40%)* | ____% | Net Monthly Rent credited in bank statement | Registered Lease Agreement, 6M Bank Credits, Municipal Tax Receipt |
| 9 | `pension` | **Pension Income** *(Retired Govt / PSU / Defence)* | [ ] Yes<br>[ ] No | ____% *(0–15%)* | 100% | Monthly Net Pension Credit | Pension Payment Order (PPO), 6M Pension A/c Passbook |
| 10 | `agriculture_income` | **Agricultural Income** | [ ] Yes<br>[ ] No | ____% *(30–50%)* | ____% | Annual Revenue / 12 (Must be supported by land records) | 7/12 Extract / Khasra-Khatauni, Patta, J-Forms, Bank Credits |
| 11 | `freelance_consulting` | **Freelance / Gig / Consulting** | [ ] Yes<br>[ ] No | ____% *(25–40%)* | ____% | 2-Year Average Annual Gross / 12 | 2Y ITR, Form 26AS with 194J TDS, Client Contracts |
| 12 | `investment_income` | **Investment / Dividend / Interest Income** | [ ] Yes<br>[ ] No | ____% *(30–50%)* | ____% | 2-Year Average Annual Yield / 12 | 2Y ITR, Demat Holding Statement, Fixed Deposit Certificates |

### 13A. Additional Income Component Rules

| Income Component | System Key | Treatment Policy | Conditions |
| :--- | :--- | :--- | :--- |
| **Annual Bonus / Performance Pay** | `bonusTreatment` | [ ] `Include 100% of 2-year average as monthly income`<br>[ ] `Include 50% of annual bonus`<br>[ ] `Strictly Exclude` | Must reflect in Form 16 / 26AS for consecutive 2 years |
| **Overtime / Production Incentives** | `overtimeTreatment` | [ ] `Include 50% if consistent for 12 months`<br>[ ] `Exclude` | Must be evidenced on regular monthly payslips |
| **Depreciation & Interest Addback (SE)** | `depreciationAddback` | [ ] `100% of depreciation added back to Net Profit`<br>[ ] `50% added back`<br>[ ] `No addback permitted` | Standard corporate finance practice for cash-flow capacity |
| **ITR Reconciliation Delta Tolerance** | `itrReconciliation` | Maximum allowable variance between income claimed on form and ITR net income before requiring formal credit deviation: | [ ] `Up to 15% delta acceptable`<br>[ ] `Up to 25% delta acceptable`<br>[ ] `Strict match with ITR required` |

---

## 14. Fixed Obligation to Income Ratio (FOIR) & Debt Servicing (`obligationsPage`)

### 14A. FOIR Slabs

> *Specifies the maximum permissible debt burden (existing EMIs + proposed Home Loan EMI) as a percentage of assessed net monthly income.*

| Net Monthly Assessed Household Income (₹) | Salaried Regular FOIR Cap (%) | Salaried Contractual FOIR (%) | Self-Employed (SEP/SENP) FOIR (%) |
| :--- | :---: | :---: | :---: |
| **Below ₹25,000 / month** | ____% | ____% | ____% |
| **₹25,000 – ₹50,000 / month** | ____% | ____% | ____% |
| **₹50,000 – ₹1,00,000 / month** | ____% | ____% | ____% |
| **₹1,00,000 – ₹2,00,000 / month** | ____% | ____% | ____% |
| **Above ₹2,00,000 / month** | ____% | ____% | ____% |
| **Flat Policy Rate (if non-tiered)** | **____%** | **____%** | **____%** |

### 14B. Obligation Sizing & Special Treatments

| Obligation Type | System Key | Bank Sizing Method / Factor | Conditions |
| :--- | :--- | :--- | :--- |
| **Running Term Loans (Auto, Home, Personal)** | `term_loan` | **100%** of actual monthly EMI | Verified via bank statement or bureau |
| **Credit Card Outstanding Limit** | `creditCardFoirMethod` `creditCardLimitPercentage` | [ ] **`5%`** of sanctioned credit limit as monthly EMI<br>[ ] **`3%`** of sanctioned credit limit<br>[ ] `5% of total outstanding balance`<br>[ ] `Ignore if paid in full each month` | PMS Standard parameter: `creditCardLimitPercentage` |
| **Overdraft (OD) / Cash Credit (CC) Lines** | `credit_line` | [ ] **`3%`** of total sanctioned drawing limit<br>[ ] **`5%`** of total sanctioned limit<br>[ ] Actual monthly interest servicing | |
| **Loans Marked for Pre-Closure** | `selectedToClose` | [ ] `Excluded from FOIR upon submission of foreclosure letter`<br>[ ] `Excluded with proof of clearance cheque / debit`<br>[ ] `Counted until physical closure NOC produced` | |
| **Residual Loan Tenure ≤ 6 Months** | `residualTenureWaiver` | Existing loans maturing within 6 months: | [ ] `Completely waived from FOIR calculations`<br>[ ] `Counted in FOIR until fully closed` |
| **Business-Paid EMIs** | `emiPaidBy: business_account` | Personal loans serviced directly from corporate/business bank account: | [ ] `Excluded from personal FOIR if 12M banking proof provided`<br>[ ] `Counted at 100% in personal FOIR` |
| **Shared Co-Borrower Liability** | `hasProofOverride` `monthlyShare` | Joint loan where applicant is one of several borrowers: | [ ] `Counted pro-rata based on actual repayment share proof`<br>[ ] `Counted 50% if joint with spouse`<br>[ ] `Counted 100% on all joint borrowers` |

---

## 15. Loan Tenure, Age at Maturity & Pricing Rules

### 15A. Tenure Boundaries

| Parameter | System Key | Salaried Policy | Self-Employed Policy | Notes |
| :--- | :--- | :---: | :---: | :--- |
| **Maximum Loan Tenure** | `maxTenureMonths` | ____ Months (e.g. `360`) | ____ Months (e.g. `240 / 300`) | Statutory 30-year cap |
| **Minimum Loan Tenure** | `minTenureMonths` | **____ Months** | **____ Months** | PMS Hard Gate parameter (Standard: `12`) |
| **Max Age at Loan Maturity** | `maxAgeAtMaturity` | ____ Years (e.g. `60 / 65`) | ____ Years (e.g. `65 / 70 / 75`) | Evaluated at projected maturity date |
| **Property Life at Maturity** | `maxPropertyLife` | Total `Property Age + Loan Tenure` must not exceed **____ Years** (Standard: `40–50 Years`) |

### 15B. Rate of Interest (ROI) & Pricing Structure

| Parameter | System Key | Standard Policy | Notes / Slabs |
| :--- | :--- | :--- | :--- |
| **External Benchmark Used** | `roiBenchmark` | [ ] `EBLR (Repo Linked)` [ ] `RLLR` [ ] `MCLR` [ ] `PLR` | RBI Repo Rate = ____% |
| **Spread over Benchmark** | `spreadOverRepo` | ____% p.a. | Floating rate spread |
| **Minimum Offer Rate** | `minRoi` | **____% p.a.** | Floor rate for highest CIBIL (800+) |
| **Maximum Offer Rate** | `maxRoi` | **____% p.a.** | Ceiling rate for baseline CIBIL |
| **Rate Type Supported** | `roiType` | [ ] `Floating` [ ] `Fixed` [ ] `Hybrid (Fixed for N years, then floating)` | |
| **Women Borrower Concession** | `gender: female` | **____ bps discount** on interest rate (e.g. `5 bps`) | Condition: Woman must be sole or first co-owner |

#### Tiered Pricing Grid by CIBIL Score

| CIBIL Score Band | Salaried Floating ROI (%) | Self-Employed Floating ROI (%) | Processing Fee (%) |
| :--- | :---: | :---: | :---: |
| **800 and Above** | ____% | ____% | ____% |
| **750 – 799** | ____% | ____% | ____% |
| **700 – 749** | ____% | ____% | ____% |
| **650 – 699** *(Deviation)* | ____% | ____% | ____% |
| **New To Credit (NTC)** | ____% | ____% | ____% |

### 15C. Processing Fees & Loan Limits

| Parameter | System Key | Policy Value |
| :--- | :--- | :--- |
| **Standard Processing Fee %** | `processingFeePercent` | **____% of loan amount + GST** |
| **Minimum Processing Fee** | `processingFeeMin` | ₹ ________ + GST |
| **Maximum Processing Fee Cap** | `processingFeeMax` | ₹ ________ + GST (or `No Cap`) |
| **Minimum Sanction Loan Amount** | `minLoanAmount` | ₹ ________ (e.g. ₹5,00,000 / ₹10,00,000) |
| **Maximum Sanction Loan Amount** | `maxLoanAmount` | ₹ ________________ (e.g. ₹10,00,00,000 or `Subject to valuation`) |
| **Prepayment / Foreclosure Penalty** | `prepaymentAllowed` `prepaymentChargePercent` | **0% for Individual Floating Loans** (Mandatory RBI Compliance) |

---

## 16. Special Concessions, Promotional Schemes & Deviation Matrix

### 16A. Segment-Specific Concessions

| Target Segment | Criteria | Special Concession Offered | Supporting Proof Required |
| :--- | :--- | :--- | :--- |
| **Women Borrower Special** | Sole or First-named Property Owner | ____ bps ROI discount + ____% PF waiver | KYC & Registered Title Deed |
| **Government / Defence Employees** | Serving or Retired armed forces / PSU | Preferential ROI: ____% · FOIR up to ____% | Service ID / Pension Book |
| **Elite Professionals (Doctors / CAs)** | MBBS, MD, CA, CS, Senior Advocates | Express turnaround + FOIR up to ____% | COP / Degree Certificate |
| **Green Building Scheme** | IGBC / GRIHA Gold/Platinum Certified | ____ bps ROI concession | Certified Builder Certificate |

### 16B. Credit Deviation & Delegation Matrix

> *Specifies policy limits that can be relaxed by delegated credit authorities without rejecting the file.*

| Credit Parameter | Standard Rule | Maximum Permissible Deviation | Sanctioning Authority |
| :--- | :--- | :--- | :--- |
| **CIBIL Score Floor** | `700 CIBIL` | Relaxed down to **____ CIBIL** | [ ] Branch Manager [ ] Regional Head [ ] Credit Committee |
| **FOIR Cap** | `50% / 60%` | Relaxed up to **____% FOIR** | [ ] Regional Credit Head [ ] Chief Risk Officer |
| **Maximum Age at Maturity** | `60 / 65 Years` | Extended up to **____ Years** | [ ] With financial co-applicant under 35 years |
| **Property Age Limit** | `30 Years` | Extended up to **____ Years** | [ ] With structural engineer stability certificate |
| **Minimum Ticket Size** | ₹ ________ | Reduced to ₹ ________ | [ ] Regional Sales Manager |

---

## 17. Offer Card & Visual Highlights Configuration (`offerCard`)

> *Governs which highlights and badges appear on your bank's offer card in the DigitalDSA DSA Comparison Portal.*

| Display Metric | Show on Offer Card? | Highlight Badge Text (Optional Marketing Copy) |
| :--- | :---: | :--- |
| **Interest Rate Range** | [x] Yes | e.g. `Lowest floating rate in sector` |
| **Processing Fee** | [x] Yes | e.g. `Zero Processing Fee Campaign` |
| **Maximum Tenure** | [x] Yes | e.g. `Up to 30 Years repayment` |
| **Maximum LTV Ratio** | [x] Yes | e.g. `90% funding available` |
| **Turnaround Time (TAT)** | [ ] Yes [ ] No | e.g. `In-principle sanction in 48 hours` |
| **Doorstep Documentation** | [ ] Yes [ ] No | e.g. `Free legal & valuation verification` |
| **Key Underwriting Advantage** | [ ] Yes [ ] No | e.g. `Highest rental income capitalization (up to 80%)` |

---

## 18. Formal Sign-Off & Underwriting Authority

| Item | Bank Official Details |
| :--- | :--- |
| **Policy Form Completed By** | |
| **Designation & Department** | |
| **Branch / Regional Office Location** | |
| **Official Corporate Email** | |
| **Direct Contact / Mobile Number** | |
| **Date of Submission** | `DD / MM / YYYY` |
| **Authorized Signature & Bank Seal** | <br><br>_________________________________________<br>*(Authorized Signatory)* |

---
*DigitalDSA Underwriting Architecture & Policy Management System (PMS) — Form V3.0 Specification Compliant.*
