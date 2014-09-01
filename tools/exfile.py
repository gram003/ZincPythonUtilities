from opencmiss.zinc.field import Field

def read_ex(region, path):
    """
    Read an ex* format file
    """
    sir = region.createStreaminformationRegion()
    sir.createStreamresourceFile(path)
    region.read(sir)

def _write_ex(region, path, domainTypes):
    """
    Write an ex* format file
    """
    sir = region.createStreaminformationRegion()
    res = sir.createStreamresourceFile(path)
    sir.setResourceDomainTypes(res, domainTypes) 
    region.write(sir)

def write_exmesh(region, path):
    """
    Write the element and node data as ex* format file
    """
    # FIXME: check that the filename suffix is .exmesh
    domainTypes = Field.DOMAIN_TYPE_NODES |\
        Field.DOMAIN_TYPE_MESH1D |\
        Field.DOMAIN_TYPE_MESH2D |\
        Field.DOMAIN_TYPE_MESH3D
    _write_ex(region, path, domainTypes)

def write_exnode(region, path):
    _write_ex(region, path, Field.DOMAIN_TYPE_NODES)

def write_exdata(region, path):
    _write_ex(region, path, Field.DOMAIN_TYPE_DATAPOINTS)

def write_exelem(region, path):
    domainTypes = Field.DOMAIN_TYPE_MESH1D |\
        Field.DOMAIN_TYPE_MESH2D |\
        Field.DOMAIN_TYPE_MESH3D
    _write_ex(region, path, domainTypes)
