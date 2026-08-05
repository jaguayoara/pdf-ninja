"""Crea un .pptx valido a mano con zipfile + XML (sin python-pptx)."""
import zipfile
from pathlib import Path

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "rels": "http://schemas.openxmlformats.org/package/2006/relationships",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}


def make_presentation_xml():
    # Slide size 16:9 (9144000 x 5143500 EMU = 25.4 x 14.29 cm)
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="{NS['a']}" xmlns:p="{NS['p']}" xmlns:r="{NS['r']}">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
  <p:sldIdLst>
    <p:sldId id="256" r:id="rId2"/>
    <p:sldId id="257" r:id="rId3"/>
    <p:sldId id="258" r:id="rId4"/>
  </p:sldIdLst>
  <p:sldSz cx="9144000" cy="5143500" type="screen16x9"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>'''


def make_slide_xml(title, table_xml=''):
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="{NS['a']}" xmlns:p="{NS['p']}" xmlns:r="{NS['r']}">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="457200" y="274680"/><a:ext cx="8229240" cy="1142640"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>
        <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="es-CL" sz="4400" b="1"/><a:t>{title}</a:t></a:r></a:p></p:txBody>
      </p:sp>
      {table_xml}
    </p:spTree>
  </p:cSld>
</p:sld>'''


def make_table_xml():
    return f'''<p:graphicFrame>
      <p:nvGraphicFramePr><p:cNvPr id="3" name="Tabla 1"/><p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr>
      <p:xfrm><a:off x="914400" y="1828800"/><a:ext cx="6400800" cy="1828800"/></p:xfrm>
      <a:graphic>
        <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">
          <a:tbl>
            <a:tblPr firstRow="1" bandRow="1"/>
            <a:tblGrid>
              <a:gridCol w="2133600"/><a:gridCol w="2133600"/><a:gridCol w="2133600"/>
            </a:tblGrid>
            <a:tr h="914400">
              <a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="es-CL" sz="2000" b="1"/><a:t>Producto</a:t></a:r></a:p></a:txBody></a:tc>
              <a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="es-CL" sz="2000" b="1"/><a:t>Cantidad</a:t></a:r></a:p></a:txBody></a:tc>
              <a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="es-CL" sz="2000" b="1"/><a:t>Precio</a:t></a:r></a:p></a:txBody></a:tc>
            </a:tr>
            <a:tr h="914400">
              <a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="es-CL" sz="1800"/><a:t>Manzanas</a:t></a:r></a:p></a:txBody></a:tc>
              <a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="es-CL" sz="1800"/><a:t>10</a:t></a:r></a:p></a:txBody></a:tc>
              <a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="es-CL" sz="1800"/><a:t>500</a:t></a:r></a:p></a:txBody></a:tc>
            </a:tr>
          </a:tbl>
        </a:graphicData>
      </a:graphic>
    </p:graphicFrame>'''


def make_rels_presentation():
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{NS['rels']}">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide2.xml"/>
  <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide3.xml"/>
</Relationships>'''


def make_slide_master():
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="{NS['a']}" xmlns:p="{NS['p']}">
  <p:cSld><p:spTree>
    <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr/>
  </p:spTree></p:cSld>
</p:sldMaster>'''


def make_content_types():
    overrides = []
    for i in range(1, 4):
        overrides.append(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="{NS['ct']}">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  {"".join(overrides)}
</Types>'''


def make_root_rels():
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{NS['rels']}">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''


def make_core_xml():
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="{NS['cp']}" xmlns:dc="{NS['dc']}" xmlns:dcterms="{NS['dcterms']}" xmlns:xsi="{NS['xsi']}">
  <dc:title>Presentacion de prueba</dc:title>
  <dc:subject>Demo</dc:subject>
  <dc:creator>Jorge Aguayo</dc:creator>
  <cp:keywords>ppt, test, demo</cp:keywords>
  <dcterms:created xsi:type="dcterms:W3CDTF">2026-08-04T18:00:00Z</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">2026-08-04T18:00:00Z</dcterms:modified>
</cp:coreProperties>'''


def make_app_xml():
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
  <Application>PDF Ninja</Application>
  <Slides>3</Slides>
</Properties>'''


def main():
    out = Path('test_ppt.pptx')
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', make_content_types())
        z.writestr('_rels/.rels', make_root_rels())
        z.writestr('docProps/core.xml', make_core_xml())
        z.writestr('docProps/app.xml', make_app_xml())
        z.writestr('ppt/presentation.xml', make_presentation_xml())
        z.writestr('ppt/_rels/presentation.xml.rels', make_rels_presentation())
        z.writestr('ppt/slideMasters/slideMaster1.xml', make_slide_master())
        z.writestr('ppt/slides/slide1.xml', make_slide_xml('Slide 1'))
        z.writestr('ppt/slides/slide2.xml', make_slide_xml('Slide 2 con tabla', make_table_xml()))
        z.writestr('ppt/slides/slide3.xml', make_slide_xml('Slide 3'))
    print(f'OK {out.name} ({out.stat().st_size} bytes)')


if __name__ == '__main__':
    main()
