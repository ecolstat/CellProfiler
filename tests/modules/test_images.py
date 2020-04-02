import io

import cellprofiler_core.measurement
import cellprofiler_core.modules.images
import cellprofiler.pipeline
import cellprofiler.workspace


def setUp():
    # The Images module needs a workspace and the workspace needs
    # an HDF5 file.
    #
    temp_fd, temp_filename = tempfile.mkstemp(".h5")
    measurements = cellprofiler_core.measurement.Measurements(filename=temp_filename)
    os.close(temp_fd)


def tearDown():
    measurements.close()
    os.unlink(temp_filename)
    assert not os.path.exists(temp_filename)


def test_load_v1():
    with open("./tests/resources/modules/images/v1.pipeline", "r") as fd:
        data = fd.read()

    pipeline = cellprofiler.pipeline.Pipeline()

    def callback(caller, event):
        assert not isinstance(event, cellprofiler.pipeline.LoadExceptionEvent)

    pipeline.add_listener(callback)
    pipeline.load(io.StringIO(data))
    assert len(pipeline.modules()) == 1
    module = pipeline.modules()[0]
    assert isinstance(module, cellprofiler_core.modules.images.Images)
    assert module.filter_choice == cellprofiler_core.modules.images.FILTER_CHOICE_CUSTOM
    assert (
        module.filter.value
        == 'or (directory does startwith "foo") (file does contain "bar")'
    )


def test_load_v2():
    with open("./tests/resources/modules/images/v2.pipeline", "r") as fd:
        data = fd.read()

    for fc, fctext in (
        (cellprofiler_core.modules.images.FILTER_CHOICE_CUSTOM, "Custom"),
        (cellprofiler_core.modules.images.FILTER_CHOICE_IMAGES, "Images only"),
        (cellprofiler_core.modules.images.FILTER_CHOICE_NONE, "No filtering"),
    ):
        pipeline = cellprofiler.pipeline.Pipeline()

        def callback(caller, event):
            assert not isinstance(event, cellprofiler.pipeline.LoadExceptionEvent)

        pipeline.add_listener(callback)
        pipeline.load(io.StringIO(data % fctext))
        assert len(pipeline.modules()) == 1
        module = pipeline.modules()[0]
        assert isinstance(module, cellprofiler_core.modules.images.Images)
        assert module.filter_choice == fc
        assert (
            module.filter.value
            == 'or (directory does startwith "foo") (file does contain "bar")'
        )


def test_filter_url():
    module = cellprofiler_core.modules.images.Images()
    module.filter_choice.value = cellprofiler_core.modules.images.FILTER_CHOICE_CUSTOM
    for url, filter_value, expected in (
        (
            "file:/TestImages/NikonTIF.tif",
            'and (file does startwith "Nikon") (extension does istif)',
            True,
        ),
        (
            "file:/TestImages/NikonTIF.tif",
            'or (file doesnot startwith "Nikon") (extension doesnot istif)',
            False,
        ),
        (
            "file:/TestImages/003002000.flex",
            'and (directory does endwith "ges") (directory doesnot contain "foo")',
            True,
        ),
        (
            "file:/TestImages/003002000.flex",
            'or (directory doesnot endwith "ges") (directory does contain "foo")',
            False,
        ),
    ):
        module.filter.value = filter_value
        check(module, url, expected)


def check(module, url, expected):
    """Check filtering of one URL using the module as configured"""
    pipeline = cellprofiler.pipeline.Pipeline()
    pipeline.add_urls([url])
    module.set_module_num(1)
    pipeline.add_module(module)
    m = cellprofiler_core.measurement.Measurements()
    workspace = cellprofiler.workspace.Workspace(pipeline, module, None, None, m, None)
    file_list = pipeline.get_filtered_file_list(workspace)
    if expected:
        assert len(file_list) == 1
        assert file_list[0] == url
    else:
        assert len(file_list) == 0


def test_filter_standard():
    module = cellprofiler_core.modules.images.Images()
    module.filter_choice.value = cellprofiler_core.modules.images.FILTER_CHOICE_IMAGES
    for url, expected in (
        ("file:/TestImages/NikonTIF.tif", True),
        ("file:/foo/.bar/baz.tif", False),
        ("file:/TestImages/foo.bar", False),
    ):
        check(module, url, expected)
